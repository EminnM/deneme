"""A polished-looking 5-slide deck whose defects are all subtle (2-6pt, near-identical colours, 1pt font
differences). build() returns ground truth [(slide, category, note)]."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from make_sloppy import tb, rect, icon

NAVY = RGBColor(0x2E, 0x5A, 0x72)
PANEL = RGBColor(0xE8, 0xEE, 0xF2)
WHITE = RGBColor(255, 255, 255)
TITLE_GAP_Y = 75   # y of the banner under slide 4's title (title text ends ~71pt, so the gap is ~4pt)


def build(path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    L_TITLE, L_TONLY = prs.slide_layouts[0], prs.slide_layouts[5]
    truth = []

    def slide(title, size=28, number=True):
        s = prs.slides.add_slide(L_TONLY)
        t = s.shapes.title
        t.left, t.top, t.width, t.height = Pt(36), Pt(24), Pt(888), Pt(60)
        t.text = title
        r = t.text_frame.paragraphs[0].runs[0]
        r.font.size, r.font.bold, r.font.name = Pt(size), True, "Calibri"
        t.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
        if number:
            tb(s.shapes, 880, 505, 44, 22, str(len(prs.slides)), 11, align=PP_ALIGN.RIGHT)
        return s

    s = prs.slides.add_slide(L_TITLE)
    s.shapes.title.text = "Altheria Mental Health Strategy"
    s.placeholders[1].text = "Board discussion document"

    # ---- 2: three cards, every defect subtle
    s = slide("Three levers will close the access gap")
    bodies = ["Train and retain more specialists outside the capital.",
              "Shift funding from hospital beds to community services.",
              "Run one coordinated awareness programme nationwide."]
    for i in range(3):
        x = 36 + i * 300
        g = s.shapes.add_group_shape()
        rect(g.shapes, x, 140, 280, 300, PANEL)
        hdr = rect(g.shapes, x, 110, 280, 30, RGBColor(46, 90, 122) if i == 1 else RGBColor(46, 90, 114))   # colour off by 8 in blue
        hdr.text_frame.text = f"Lever {i + 1}"
        r = hdr.text_frame.paragraphs[0].runs[0]; r.font.size, r.font.bold = Pt(14), True; r.font.color.rgb = WHITE
        g.shapes.add_picture(icon((46, 125, 140)), Pt(x + 122), Pt(150 + (2 if i == 1 else 0)), Pt(36), Pt(36))
        tb(g.shapes, x + (13 if i == 2 else 10), 200, 260, 200, bodies[i], 13 if i == 1 else 14)
    truth += [(2, "Consistency", "header colour differs by 8 in blue"), (2, "Alignment", "icon 2pt low"),
              (2, "Alignment", "col 3 text 3pt right"), (2, "Consistency", "col 2 text 13pt vs 14pt")]

    # ---- 3: process boxes + arrows
    s = slide("Four steps from diagnosis to scale")
    xs = [36, 266, 496, 733]                                   # last gap 37pt instead of 30pt
    labels = ["Diagnose", "Design", "Pilot", "Scale"]
    for i, (x, lb) in enumerate(zip(xs, labels)):
        b = rect(s.shapes, x, 160, 200, 90, NAVY)
        b.text_frame.text = lb
        r = b.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(18); r.font.color.rgb = WHITE
        r.font.name = "Arial" if i == 2 else "Calibri"                 # one box in Arial
    for i in range(3):
        y2 = 206 if i == 1 else 205                                    # arrow 2 is ~1.9 degrees off
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Pt(xs[i] + 202), Pt(205), Pt(xs[i + 1] - 2), Pt(y2))
    tb(s.shapes, 36, 470, 700, 16, "Source: programme team analysis", 9)               # 9pt vs 10pt minimum
    rect(s.shapes, 840, 440, 56, 30, RGBColor(0xD8, 0xD8, 0xD8))                      # faint grey leftover box nobody noticed
    truth += [(3, "Leftover graphics", "faint grey box"), (3, "Spacing", "last gap 37 vs 30"), (3, "Lines and arrows", "arrow 1.9 degrees"),
              (3, "Consistency", "Arial box"), (3, "Readability", "9pt footnote")]

    # ---- 4: KPI tiles, title squeezed
    s = slide("Key figures at a glance")
    kp = [("41%", "untreated"), ("18", "beds / 100k"), ("$12", "per capita"), ("6 mo", "wait")]
    for i, (v, l) in enumerate(kp):
        y = 127 if i == 2 else 130                                      # tile 3 is 3pt high
        fill = RGBColor(30, 70, 118) if i == 1 else RGBColor(30, 70, 110)   # tile 2 differs by 8 in blue
        t = rect(s.shapes, 36 + i * 225, y, 200, 110, fill)
        t.text_frame.text = v
        r = t.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(32); r.font.bold = True; r.font.color.rgb = WHITE
        tb(s.shapes, 36 + i * 225 + 10, y + 70, 180, 24, l, 14, color=WHITE)
    rect(s.shapes, 36, TITLE_GAP_Y, 888, 6, RGBColor(46, 125, 140))      # banner very close under the title
    truth += [(4, "Alignment", "tile 3 is 3pt high"), (4, "Consistency", "tile 2 shade"),
              (4, "Titles", "banner ~4pt under title")]

    # ---- 5: bullets overflow slightly, title 27pt, no page number
    s = slide("What we recommend", size=27, number=False)
    box = tb(s.shapes, 36, 120, 880, 112,
             "Fund the workforce plan in year one.\nMove 20% of bed funding to community care.\n"
             "Appoint one accountable programme director.\nPublish quarterly access figures.\nReview progress with the board each term.\nReport results to the ministry.", 16)
    truth += [(5, "Text fit", "bullets overflow by a few pt"), (5, "Consistency", "title 27pt"),
              (5, "Consistency", "no page number")]
    prs.save(path)
    return truth


if __name__ == "__main__":
    print(build(sys.argv[1]))
