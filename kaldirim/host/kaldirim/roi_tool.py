"""Draw the gate line or zone polygon on a live frame and print the config snippet.

    python -m kaldirim.roi_tool            # grabs one frame from stream_url
    python -m kaldirim.roi_tool frame.jpg  # or use a saved frame

Left click adds a point. Right click removes the last one. Enter prints the snippet
and saves roi.png next to the data dir so you can check it later. Esc quits.
Gate = 2 points. Zone = 3 or more.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import yaml

from . import config


def grab_frame(url: str):
    cap = cv2.VideoCapture(url)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"could not read a frame from {url}")
    return frame


def main() -> None:
    cfg = config.load()
    if len(sys.argv) > 1:
        frame = cv2.imread(sys.argv[1])
    else:
        frame = grab_frame(cfg["stream_url"])
    pts: list[tuple[int, int]] = []

    def redraw():
        img = frame.copy()
        for i, p in enumerate(pts):
            cv2.circle(img, p, 5, (0, 0, 255), -1)
            if i:
                cv2.line(img, pts[i - 1], p, (0, 255, 255), 2)
        if len(pts) >= 3:
            cv2.line(img, pts[-1], pts[0], (0, 255, 255), 1)
        cv2.putText(img, f"{len(pts)} pts  (2 = gate, 3+ = zone)  Enter=save Esc=quit",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("roi", img)
        return img

    def on_mouse(ev, x, y, flags, param):
        if ev == cv2.EVENT_LBUTTONDOWN:
            pts.append((x, y))
        elif ev == cv2.EVENT_RBUTTONDOWN and pts:
            pts.pop()
        redraw()

    cv2.namedWindow("roi")
    cv2.setMouseCallback("roi", on_mouse)
    img = redraw()
    while True:
        k = cv2.waitKey(50) & 0xFF
        if k == 27:
            break
        if k in (10, 13):
            img = redraw()
            out = Path(cfg["data_dir"], "roi.png")
            cv2.imwrite(str(out), img)
            if len(pts) == 2:
                print(yaml.safe_dump({"count": {"mode": "gate", "gates": [{"name": "gate1", "points": [list(p) for p in pts]}]}},
                                     allow_unicode=True))
                print("add more gates to the list with their own names; run the tool again for each")
            elif len(pts) >= 3:
                print(yaml.safe_dump({"count": {"mode": "zone", "zone": [list(p) for p in pts]}}))
            else:
                print("need 2 points for a gate or 3+ for a zone")
            print(f"preview saved to {out}")
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
