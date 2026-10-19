"""Pure geometry used by the counter. No OpenCV so it is easy to test."""
from __future__ import annotations

Point = tuple[float, float]


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_cross(p1: Point, p2: Point, q1: Point, q2: Point) -> bool:
    """True if segment p1-p2 crosses segment q1-q2 (proper or touching)."""
    d1 = _orient(q1, q2, p1)
    d2 = _orient(q1, q2, p2)
    d3 = _orient(p1, p2, q1)
    d4 = _orient(p1, p2, q2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    # touching cases
    def on(a, b, c):
        return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
    if d1 == 0 and on(q1, q2, p1): return True
    if d2 == 0 and on(q1, q2, p2): return True
    if d3 == 0 and on(p1, p2, q1): return True
    if d4 == 0 and on(p1, p2, q2): return True
    return False


def point_in_polygon(pt: Point, poly: list[Point]) -> bool:
    """Ray casting. Works for concave polygons."""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                inside = not inside
    return inside


def ground_point(box_xyxy) -> Point:
    """Bottom-center of a bounding box: where the wheels touch the ground."""
    x1, y1, x2, y2 = box_xyxy
    return ((x1 + x2) / 2.0, y2)


class CountRule:
    """Decides, per track id, when a rider gets counted exactly once.

    gate mode: count when the segment from the previous ground point to the current one
               crosses the gate line. Robust at low fps and with partial views.
    zone mode: count after `min_frames` consecutive ground points inside the polygon.
    """

    def __init__(self, mode: str, gate=None, zone=None, min_frames: int = 3, cooldown_s: float = 2.0):
        if mode not in ("gate", "zone"):
            raise ValueError("mode must be 'gate' or 'zone'")
        self.mode = mode
        self.gate = [tuple(p) for p in (gate or [])]
        self.zone = [tuple(p) for p in (zone or [])]
        self.min_frames = min_frames
        self.cooldown_s = cooldown_s
        self._last_pt: dict[int, Point] = {}
        self._streak: dict[int, int] = {}
        self._counted_at: dict[int, float] = {}

    def update(self, track_id: int, pt: Point, now: float) -> bool:
        """Feed one observation. Returns True exactly when this observation triggers a count."""
        last_count = self._counted_at.get(track_id)
        if last_count is not None and now - last_count < self.cooldown_s:
            self._last_pt[track_id] = pt
            return False

        hit = False
        if self.mode == "gate":
            prev = self._last_pt.get(track_id)
            if prev is not None and segments_cross(prev, pt, self.gate[0], self.gate[1]):
                hit = True
        else:
            if point_in_polygon(pt, self.zone):
                self._streak[track_id] = self._streak.get(track_id, 0) + 1
                if self._streak[track_id] == self.min_frames:
                    hit = True
            else:
                self._streak[track_id] = 0

        self._last_pt[track_id] = pt
        if hit:
            self._counted_at[track_id] = now
        return hit

    def forget_stale(self, now: float, max_age_s: float = 60.0) -> None:
        """Drop state for tracks not seen in a while so memory stays flat."""
        stale = [t for t, at in self._counted_at.items() if now - at > max_age_s]
        for t in stale:
            self._counted_at.pop(t, None)
            self._last_pt.pop(t, None)
            self._streak.pop(t, None)


def auto_crop(points: list[Point], frame_w: int, frame_h: int, margin: int) -> tuple[int, int, int, int]:
    """Smallest frame-aligned box around `points` plus `margin` px, clamped to the frame.

    Returns (x, y, w, h). Running the detector on this crop instead of the full frame keeps
    small, distant riders at native resolution.
    """
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x1 = max(0, int(min(xs) - margin))
    y1 = max(0, int(min(ys) - margin))
    x2 = min(frame_w, int(max(xs) + margin))
    y2 = min(frame_h, int(max(ys) + margin))
    return x1, y1, max(1, x2 - x1), max(1, y2 - y1)
