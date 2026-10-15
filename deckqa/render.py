"""Optional: render to PNG with red circles around problems (needs soffice + pdftoppm)."""
import glob, os, subprocess, tempfile
from PIL import Image, ImageDraw


def render(pptx, issues, deck, outdir, dpi=80):
    os.makedirs(outdir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, pptx],
                       check=True, capture_output=True, timeout=180)
        pdf = glob.glob(os.path.join(tmp, "*.pdf"))[0]
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf, os.path.join(outdir, "slide")], check=True)
    scale = dpi / 72.0
    for path in sorted(glob.glob(os.path.join(outdir, "slide-*.png"))):
        no = int(os.path.basename(path)[6:-4])
        mine = [i for i in issues if i.slide == no and i.bbox]
        if not mine:
            continue
        im = Image.open(path).convert("RGB")
        d = ImageDraw.Draw(im)
        for i in mine:
            l, t, r, b = [v * scale for v in i.bbox]
            d.ellipse((l - 6, t - 6, r + 6, b + 6), outline=(220, 30, 30), width=3)
        im.save(path)
