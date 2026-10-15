from dataclasses import dataclass, field


@dataclass
class Issue:
    slide: int
    category: str
    message: str
    ids: list = field(default_factory=list)      # shape ids involved
    bbox: tuple = None                           # (l, t, r, b) points, for marking
    fixable: bool = False
    fix: dict = None                             # machine-readable fix instruction
    status: str = "open"                         # open | fixed

    def to_dict(self):
        return dict(slide=self.slide, category=self.category, message=self.message,
                    ids=self.ids, bbox=self.bbox, fixable=self.fixable, status=self.status)
