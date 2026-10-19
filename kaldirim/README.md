# kaldirim

Counts motorcycles riding on the pavement in front of a fixed indoor camera and publishes
**numbers, not people**: a nightly post with the day's count and hourly curve, and a static
dashboard. Full clips stay on the host for official reports only.

```
Deneyap Kart + Kamera  --Wi-Fi MJPEG-->  host (Pi / laptop)
                                          ├─ counter.py     YOLO + ByteTrack, gate-line crossing, SQLite, local clips
                                          ├─ dashboard.py   data/site/index.html (static, numbers only)
                                          ├─ post_daily.py  nightly text + hourly chart to X (dry run by default)
                                          └─ export_report.py  one clip + note for the police app
```

## 1. Firmware

`firmware/deneyap_cam_stream/deneyap_cam_stream.ino`

1. Arduino IDE → Boards Manager URL
   `https://raw.githubusercontent.com/deneyapkart/deneyapkart-arduino-core/master/package_deneyapkart_index.json`,
   install **Deneyap**, select your Deneyap Kart revision.
2. Put your Wi-Fi name and password in the two constants, flash.
3. Serial monitor at 115200 prints the stream URL, `http://<ip>/stream`.
   Open `http://<ip>/jpg` in a browser to check framing.

The board lives inside the room, behind the window, well back from the glass.

## 2. Host

```
cd host
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml      # edit stream_url
python -m kaldirim.roi_tool             # click 2 points for a gate line, Enter, paste into config.yaml
python -m kaldirim.counter              # runs forever; logs each count
```

**Gate vs zone.** With a partial or oblique view, draw a short *gate* line across the pavement
where riders must pass; a track is counted once when it crosses it. This works at the 2 to 4 fps a
Raspberry Pi gives. With a clean wide view you can use a *zone* polygon instead.

**Checking the numbers.** Every count has a clip in `data/clips/`. Review a day's clips before you
publish the first week, tune `conf`, the gate position and `cooldown_s`, and keep the false-positive
rate honest. The dashboard's method note tells readers exactly how the count is made.

## 3. Publishing

```
python -m kaldirim.dashboard      # writes data/site/index.html; host it on GitHub Pages or similar
python -m kaldirim.post_daily     # prints the post and chart; set post.dry_run: false to send
```

Cron, nightly at 22:05:

```
5 22 * * *  cd /path/to/host && .venv/bin/python -m kaldirim.dashboard && .venv/bin/python -m kaldirim.post_daily
```

X API keys come from developer.x.com (app with read and write). Mark the account as automated in
its settings.

## 4. Police reports

```
python -m kaldirim.export_report 123          # one event
python -m kaldirim.export_report 2026-10-18   # a whole day
```

Files land in `data/exports/` with a sidecar note. Send the clear cases, not all of them.

## What never leaves the host

Frames, clips, plates, faces, the camera position. The post and the dashboard contain counts,
times and a method note. Keep the account bio to "a street in Istanbul".

## Tests

```
cd host && pip install pytest && python -m pytest tests
```
