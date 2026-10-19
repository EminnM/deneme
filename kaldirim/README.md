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

**High window, far pavement.** From 30 m or more the rider is a few dozen pixels in a full frame.
Keep the firmware at UXGA (1600x1200) and leave `model.crop: "auto"` on: the detector then runs on
a tight box around the gate at native resolution rather than on a downscaled whole frame. Check the
first day's clips to confirm riders are being picked up; if not, lower `conf` to 0.25 before
anything else.

**Model choice.** Default is the COCO-pretrained `yolo26n.pt` (class 3, motorcycle). COCO is mostly
street-level photos, so a steep downward view at 40 m is outside what it saw in training. If the
first day's clips show misses, switch to a VisDrone-trained checkpoint, which is drone-viewpoint
data with a `motor` class (index 9): for example `dronefreak/visdrone-yolo26m` on Hugging Face,
download `best.pt`, set `model.weights` to it and `model.classes` to `[9]`. VisDrone weights are
licensed for academic and non-commercial use, which this is.

**After dark.** The OV2640 is weak in low light. Under street lighting it still sees headlights and
shapes, but expect an undercount in the evening. The before-and-after comparison is still fair as
long as both periods have the same hours of darkness, so compare within the same season.

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

## 4. Sharing an image

```
python -m kaldirim.export_image 123
```

Writes `data/exports/<clip>_masked.png`: the rider and bike cut out by a segmentation model,
placed on a flat background, downscaled below plate and face resolution and re-upscaled.
No signage, no curb, no perspective lines, no metadata. This is the only image form meant
to leave the host. Never post a raw frame or clip.

## 5. Measuring whether it helps

Set `post.campaign_start` to the date of your first public post. The dashboard then shows the
daily average before and since, with the day counts. Run the counter for at least two weeks
before the first post so the "before" number means something, and expect noise from weather
and school holidays.

## 6. Police reports

```
python -m kaldirim.export_report 123          # one event
python -m kaldirim.export_report 2026-10-18   # a whole day
```

Files land in `data/exports/` with a sidecar note. Send the clear cases, not all of them.

Submission is manual by design: the Gereği Yapıldı and EGM Mobil apps have no public API, every
report is made under your e-Devlet identity and attested by you, and a script hammering them with
a hundred reports a day gets the account flagged, not the riders fined. A fine needs a readable
plate, so clips are kept at full stream resolution; switch the firmware to `FRAMESIZE_UXGA` if
plates are still too small at your distance (lower fps, the gate rule copes).

## What never leaves the host

Frames, clips, plates, faces, the camera position. The post and the dashboard contain counts,
times and a method note. Keep the account bio to "a street in Istanbul".

## Tests

```
cd host && pip install pytest && python -m pytest tests
```
