"""A dense consulting-style slide (title, six grouped columns with tab, icon, body text)
with optional seeded defects. Everything lives inside groups, like real consulting decks."""
import io
from PIL import Image
from pptx import Presentation
from pptx.util import Pt, Emu, Inches
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_AUTO_SIZE

ICON = None


def _icon_png():
    im = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    for x in range(16, 48):
        for y in range(16, 48):
            im.putpixel((x, y), (30, 70, 110, 255))
    b = io.BytesIO(); im.save(b, "PNG"); b.seek(0)
    return b


def _text(shapes, l, t, w, h, text, size, bold=False, fixed=True):
    b = shapes.add_textbox(Pt(l), Pt(t), Pt(w), Pt(h))
    tf = b.text_frame
    tf.word_wrap = True
    if fixed:
        tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.text = text
    r = tf.paragraphs[0].runs[0]
    r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Arial"
    return b


def build(path, defects=True):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    s = prs.slides.add_slide(prs.slide_layouts[6])
    sh = s.shapes
    title_text = "Altheria faces significant challenges in tackling mental health across the spectrum"
    # title (not a placeholder): 2 lines at 24pt in a 900pt wide box
    _text(sh, 36, 20, 880, 60, title_text, 24)
    col_w, gap, x0, y0 = 140, 10, 36, (84 if defects else 125)   # defect: content pushed up under the title
    bodies = ["Large share of untreated patients, especially mild to moderate cases",
              "Overcrowded mental hospitals jeopardized quality",
              "Confusion about roles and responsibilities for each entity",
              "Disintegrated care creates harder navigation of the system",
              "Isolated facilities reinforce myths about patients",
              "Gaps in service provision and workforce demand"]
    for i in range(6):
        x = x0 + i * (col_w + gap)
        g = sh.add_group_shape()
        gs = g.shapes
        panel = gs.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y0 + 40), Pt(col_w), Pt(300))
        panel.fill.solid(); panel.fill.fore_color.rgb = RGBColor(0xE4, 0xEC, 0xF1); panel.line.fill.background()
        head = gs.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y0), Pt(col_w), Pt(40))
        head.fill.solid(); head.fill.fore_color.rgb = RGBColor(0x2E, 0x5A, 0x72); head.line.fill.background()
        icon_dx, icon_dy = (col_w - 30) / 2, 5
        tab_dy = 0
        body_w = col_w - 12
        if defects:
            if i == 2:
                tab_dy = 22                       # staggered tab (peer outlier)
            if i == 4:
                icon_dx, icon_dy = icon_dx + 5, icon_dy - 4   # icon off from siblings
            if i == 3:
                icon_dx += 3                      # icon nearly (not quite) centred
            if i == 1:
                body_w = col_w + 40               # text box spills into the next column
        pic = gs.add_picture(_icon_png(), Pt(x + icon_dx), Pt(y0 + icon_dy), Pt(30), Pt(30))
        tab = _text(gs, x + 6, y0 + 44 + tab_dy, col_w - 12, 22, f"Theme {i + 1}", 11, bold=True)
        _text(gs, x + 6, y0 + 74, body_w, 200, bodies[i], 11)
    if defects:
        # title text crashes into the content below it: lengthen the title so it wraps to 3 lines
        pass
    prs.save(path)


if __name__ == "__main__":
    import sys
    build(sys.argv[1], defects=(len(sys.argv) < 3 or sys.argv[2] != "clean"))
