"""Optional: render to PNG with red circles around problems (needs soffice + pdftoppm)."""
import glob, os, shutil, subprocess, tempfile
from PIL import Image, ImageDraw


def _tool(names, extra=()):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for p in extra:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("could not find " + " / ".join(names))


def render(pptx, issues, deck, outdir, dpi=80, annotate=True):
    os.makedirs(outdir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([_tool(["soffice", "soffice.exe", "libreoffice"], [r"C:\\Program Files\\LibreOffice\\program\\soffice.exe", r"C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe"]), "--headless", "--convert-to", "pdf", "--outdir", tmp, pptx],
                       check=True, capture_output=True, timeout=180)
        pdf = glob.glob(os.path.join(tmp, "*.pdf"))[0]
        subprocess.run([_tool(["pdftoppm", "pdftoppm.exe"]), "-png", "-r", str(dpi), pdf, os.path.join(outdir, "slide")], check=True)
    scale = dpi / 72.0
    result = {}
    for path in sorted(glob.glob(os.path.join(outdir, "slide-*.png"))):
        no = int(os.path.basename(path)[6:-4].lstrip('0') or 0)
        result[no] = path
        mine = [i for i in issues if i.slide == no and i.bbox] if annotate else []
        if not mine:
            continue
        im = Image.open(path).convert("RGB")
        d = ImageDraw.Draw(im)
        for i in mine:
            l, t, r, b = [v * scale for v in i.bbox]
            d.ellipse((l - 6, t - 6, r + 6, b + 6), outline=(220, 30, 30), width=3)
        im.save(path)
    return result
