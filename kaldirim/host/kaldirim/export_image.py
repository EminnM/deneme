"""Make a shareable image from one event: the rider and bike cut out onto a flat background.

    python -m kaldirim.export_image 123

Output: data/exports/<clip name>_masked.png, PNG with no metadata.
What is removed: the whole background (buildings, signage, road, curb, perspective lines),
and detail below plate and face resolution (the cutout is downscaled hard, then upscaled).
What remains: the silhouette of a motorcycle with a rider on it, and nothing that says where.

Needs the segmentation weights (yolov8n-seg.pt, auto-downloaded). Falls back to a heavily
pixelated box crop if no mask is found.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

from . import config, db

PERSON, MOTORCYCLE = 0, 3
BG = (236, 235, 233)        # flat light surface, BGR
MAX_H = 200                 # cutout height in px before the stylising upscale; kills plate/face detail


def frame_at_count(clip_path: str, pre_s: float):
    cap = cv2.VideoCapture(clip_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 8.0
    idx = max(0, int(round(pre_s * fps)) - 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    if not ok:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def _iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    return inter / (area(a) + area(b) - inter)


def rider_mask(frame, target_xy, model):
    """Union mask of the motorcycle nearest `target_xy` and any person overlapping it, or None."""
    res = model(frame, classes=[PERSON, MOTORCYCLE], conf=0.3, verbose=False)[0]
    if res.masks is None or len(res.boxes) == 0:
        return None, None
    h, w = frame.shape[:2]
    boxes = res.boxes.xyxy.tolist()
    cls = res.boxes.cls.int().tolist()
    masks = res.masks.data.cpu().numpy()
    bikes = [i for i, c in enumerate(cls) if c == MOTORCYCLE]
    if not bikes:
        return None, None
    tx, ty = target_xy
    best = min(bikes, key=lambda i: (((boxes[i][0] + boxes[i][2]) / 2 - tx) ** 2 + (boxes[i][3] - ty) ** 2))
    keep = [best] + [i for i, c in enumerate(cls) if c == PERSON and _iou(boxes[i], boxes[best]) > 0.05]
    m = np.zeros((masks.shape[1], masks.shape[2]), dtype=np.uint8)
    for i in keep:
        m |= (masks[i] > 0.5).astype(np.uint8)
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
    xs, ys = np.where(m.any(axis=0))[0], np.where(m.any(axis=1))[0]
    if len(xs) == 0:
        return None, None
    box = (int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1)
    return m, box


def stylise(cut, mask_crop):
    """Downscale to MAX_H, then upscale with nearest neighbour so detail is gone for good."""
    h, w = cut.shape[:2]
    s = min(1.0, MAX_H / max(1, h))
    small = cv2.resize(cut, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
    small_m = cv2.resize(mask_crop, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    canvas = np.full_like(small, BG)
    canvas[small_m > 0] = small[small_m > 0]
    pad = max(8, small.shape[0] // 8)
    canvas = cv2.copyMakeBorder(canvas, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=BG)
    return cv2.resize(canvas, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)


def pixelate_fallback(frame, cx, cy, size=160):
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(cx - size)), max(0, int(cy - size * 1.5))
    x2, y2 = min(w, int(cx + size)), min(h, int(cy + size * 0.3))
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    tiny = cv2.resize(crop, (24, max(1, int(24 * crop.shape[0] / crop.shape[1]))), interpolation=cv2.INTER_AREA)
    return cv2.resize(tiny, (crop.shape[1] * 2, crop.shape[0] * 2), interpolation=cv2.INTER_NEAREST)


def export(con, cfg: dict, event_id: int, model) -> Path | None:
    row = con.execute("SELECT id, clip_path, x, y FROM events WHERE id=?", (event_id,)).fetchone()
    if not row or not row[1] or not Path(row[1]).exists():
        print(f"event {event_id}: no clip on disk")
        return None
    frame = frame_at_count(row[1], cfg["clip"]["pre_s"])
    if frame is None:
        print(f"event {event_id}: clip unreadable")
        return None
    mask, box = rider_mask(frame, (row[2], row[3]), model)
    if mask is not None:
        x1, y1, x2, y2 = box
        img = stylise(frame[y1:y2, x1:x2], mask[y1:y2, x1:x2])
    else:
        img = pixelate_fallback(frame, row[2], row[3])
        if img is None:
            return None
        print(f"event {event_id}: no mask found, used pixelated crop")
    out = Path(cfg["data_dir"], "exports", Path(row[1]).stem + "_masked.png")
    cv2.imwrite(str(out), img)   # PNG via OpenCV carries no EXIF or location metadata
    print(out)
    return out


def main() -> None:
    cfg = config.load()
    con = db.connect(cfg["data_dir"])
    from ultralytics import YOLO
    model = YOLO(cfg.get("model", {}).get("seg_weights", "yolov8n-seg.pt"))
    for a in sys.argv[1:]:
        export(con, cfg, int(a), model)


if __name__ == "__main__":
    main()
