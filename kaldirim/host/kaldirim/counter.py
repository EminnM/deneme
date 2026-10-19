"""Main loop: read the Deneyap stream, track motorcycles, count crossings, archive clips.

    python -m kaldirim.counter

Runs forever and reconnects when the stream drops. Nothing here posts anywhere.
"""
from __future__ import annotations

import collections
import logging
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2

from . import config, db
from .geometry import CountRule, ground_point

log = logging.getLogger("kaldirim")


class ClipWriter:
    """Keeps a ring buffer of recent frames and writes pre+post clips per event."""

    def __init__(self, clip_dir: Path, pre_s: float, post_s: float, width: int, fps_guess: float = 8.0):
        self.clip_dir = clip_dir
        self.pre_s, self.post_s, self.width = pre_s, post_s, width
        self.buf: collections.deque = collections.deque()  # (t, small_frame)
        self.pending: list[tuple[float, cv2.VideoWriter, str]] = []
        self.fps_guess = fps_guess

    def _small(self, frame):
        h, w = frame.shape[:2]
        if w <= self.width:
            return frame
        return cv2.resize(frame, (self.width, int(h * self.width / w)))

    def push(self, t: float, frame) -> None:
        small = self._small(frame)
        self.buf.append((t, small))
        while self.buf and t - self.buf[0][0] > self.pre_s:
            self.buf.popleft()
        for item in list(self.pending):
            end_t, writer, _ = item
            writer.write(small)
            if t >= end_t:
                writer.release()
                self.pending.remove(item)

    def start(self, t: float, event_id: int, when: datetime) -> str:
        name = when.strftime("%Y%m%d_%H%M%S") + f"_{event_id}.mp4"
        path = self.clip_dir / name
        if not self.buf:
            return str(path)
        h, w = self.buf[0][1].shape[:2]
        if len(self.buf) >= 2:
            span = self.buf[-1][0] - self.buf[0][0]
            fps = max(2.0, min(30.0, (len(self.buf) - 1) / span)) if span > 0 else self.fps_guess
        else:
            fps = self.fps_guess
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        for _, f in self.buf:
            writer.write(f)
        self.pending.append((t + self.post_s, writer, str(path)))
        return str(path)


def open_stream(url: str):
    while True:
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            log.info("stream open: %s", url)
            return cap
        log.warning("stream not reachable, retrying in 5s")
        time.sleep(5)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = config.load()
    tz = ZoneInfo(cfg.get("timezone", "Europe/Istanbul"))
    con = db.connect(cfg["data_dir"])

    from ultralytics import YOLO  # imported late: slow import, optional for tests
    m = cfg["model"]
    model = YOLO(m["weights"])

    c = cfg["count"]
    rule = CountRule(c["mode"], gate=c.get("gate"), zone=c.get("zone"),
                     min_frames=c.get("zone_min_frames", 3), cooldown_s=c.get("cooldown_s", 2.0))
    cl = cfg["clip"]
    clips = ClipWriter(Path(cfg["data_dir"], "clips"), cl["pre_s"], cl["post_s"], cl["width"])

    cap = open_stream(cfg["stream_url"])
    frames = 0
    last_log = time.time()
    while True:
        ok, frame = cap.read()
        now = time.time()
        if not ok:
            log.warning("frame read failed, reopening stream")
            cap.release()
            cap = open_stream(cfg["stream_url"])
            continue
        frames += 1
        clips.push(now, frame)

        res = model.track(frame, persist=True, imgsz=m["imgsz"], conf=m["conf"],
                          classes=m["classes"], tracker=m.get("tracker", "bytetrack.yaml"),
                          verbose=False)[0]
        if res.boxes is not None and res.boxes.id is not None:
            ids = res.boxes.id.int().tolist()
            confs = res.boxes.conf.tolist()
            for box, tid, conf in zip(res.boxes.xyxy.tolist(), ids, confs):
                pt = ground_point(box)
                if rule.update(tid, pt, now):
                    when = datetime.now(tz)
                    eid = db.insert_event(con, when.isoformat(timespec="seconds"), when.strftime("%Y-%m-%d"),
                                          when.hour, tid, float(conf), int(pt[0]), int(pt[1]), None)
                    path = clips.start(now, eid, when)
                    con.execute("UPDATE events SET clip_path=? WHERE id=?", (path, eid))
                    con.commit()
                    log.info("count #%d track=%d conf=%.2f clip=%s", eid, tid, conf, Path(path).name)
        rule.forget_stale(now)

        if now - last_log > 60:
            log.info("alive: %.1f fps", frames / (now - last_log))
            frames, last_log = 0, now


if __name__ == "__main__":
    main()
