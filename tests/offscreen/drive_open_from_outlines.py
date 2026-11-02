"""Double-click Outlines rows in Cleanup, outside RoboFont (issue #12)."""
import sys
import tempfile
import types
from pathlib import Path

lib = sys.argv[1]


def module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


sys.modules["mojo"] = None
import ezui  # noqa: E402,F401
import vanilla  # noqa: E402,F401
del sys.modules["mojo"]
mojo = module("mojo")
mojo.__path__ = []
current = {"glyph": None}
opened = []         # OpenFont calls
open_fonts = []     # what AllFonts returns


class FakeGlyph:
    contours = ()

    def __init__(self, path, layer, name):
        self.font = types.SimpleNamespace(path=str(path) if path else None)
        self.layer = types.SimpleNamespace(name=layer)
        self.name = name

    def __iter__(self):
        return iter(self.contours)


class FakeFont:
    def __init__(self, path):
        self.path = str(path)
        from defcon import Font
        self._font = Font(self.path)

    def naked(self):
        return self._font

    def getLayer(self, name):
        return types.SimpleNamespace(__getitem__=None, name=name, font=self,
                                     get=lambda glyph: FakeGlyph(self.path, name, glyph))

    def __getitem__(self, name):
        return FakeGlyph(self.path, "public.default", name)


def open_font(path, showInterface=True):
    opened.append((Path(path).name, showInterface))
    font = FakeFont(path)
    open_fonts.append(font)
    return font


def open_glyph_window(glyph):
    current["glyph"] = glyph


module("mojo.UI", GetFile=lambda **k: None, OpenGlyphWindow=open_glyph_window,
       CurrentGlyphWindow=lambda: (types.SimpleNamespace(getGlyph=lambda: current["glyph"])
                                   if current["glyph"] else None))
module("mojo.roboFont", AllFonts=lambda: list(open_fonts), OpenFont=open_font)

import AppKit  # noqa: E402
AppKit.NSApplication.sharedApplication()
sys.path.insert(0, lib)

from defcon import Font  # noqa: E402
from fontTools.designspaceLib import (  # noqa: E402
    AxisDescriptor, DesignSpaceDocument, SourceDescriptor,
)
from tdbk_rftools.cleanup import compatibility, window as cleanup  # noqa: E402


def draw(glyph, *contours):
    pen = glyph.getPointPen()
    for points in contours:
        pen.beginPath()
        for kind, x, y in points:
            pen.addPoint((x, y), kind)
        pen.endPath()


def d(x, size=100, reverse=False, start=0):
    """A D shape: one curve, so its start point shows by type."""
    points = [("line", x, 0), ("offcurve", x + size, 0), ("offcurve", x + size, size),
              ("curve", x, size)]
    if reverse:
        points = [("line", x, 0), ("curve", x, size), ("offcurve", x + size, size),
                  ("offcurve", x + size, 0)]
        points[0], points[1] = ("curve", x, 0), ("line", x, size)
    return points[start:] + points[:start]


root = Path(tempfile.mkdtemp())
paths = {name: root / f"{name}.ufo" for name in ("Light", "Regular", "Bold")}
fonts = {name: Font() for name in paths}
for name in ("A", "B", "C"):
    draw(fonts["Regular"].newGlyph(name), d(0), d(200))
draw(fonts["Light"].newGlyph("A"), d(0, 80, start=1), d(200, 80))        # start point
draw(fonts["Bold"].newGlyph("A"), d(200, 130), d(0, 130))                # contour order
draw(fonts["Light"].newGlyph("B"), d(0, 80), d(200, 80))                 # compatible
draw(fonts["Bold"].newGlyph("B"), d(0, 130), d(200, 130, start=2))       # start point
draw(fonts["Light"].newGlyph("C"), d(0, 80))                             # contour count
for name, font in fonts.items():
    font.save(str(paths[name]))
document = DesignSpaceDocument()
axis = AxisDescriptor()
axis.name, axis.tag, axis.minimum, axis.default, axis.maximum = "Weight", "wght", 0, 400, 1000
document.addAxis(axis)
for name, weight in (("Light", 0), ("Regular", 400), ("Bold", 1000)):
    source = SourceDescriptor()
    source.path, source.name, source.location = str(paths[name]), name, {"Weight": weight}
    document.addSource(source)
designspace = root / "Test.designspace"
document.write(designspace)

c = cleanup.open_window()
c.designspace_path = str(designspace)
c._load()
rows = [(item["glyph"], item["mismatches"]) for item in c.outlines.outlineRows.get()]
print("OUTLINES:", rows)


class Table:
    def __init__(self, row):
        self.row = row

    def clickedRow(self):
        return self.row


def double_click(row):
    sender = types.SimpleNamespace(getNSTableView=lambda: Table(row))
    c._open_outline_row(sender)
    w = compatibility._window
    glyph = current["glyph"]
    print(f"ROW {row}: glyph {glyph.name if glyph else None} in "
          f"{Path(glyph.font.path).name if glyph else None} · tab {w.w.tabs.get()} · "
          f"status {w.w.status.get()!r} · compare "
          f"{w._comparison.label if w._comparison else None} · popup "
          f"{w.points.comparison.getItems()[w.points.comparison.get()] if w._choices else None}")


# The user is on Regular B, comparing with Light: the landing must still
# switch the comparison to the Default once Bold A is current.
current["glyph"] = FakeGlyph(paths["Regular"], "public.default", "B")
compatibility.open_window()
compatibility._window._comparison = next(s for s in c.session.sources if s.label == "Light")
compatibility.refresh_open_window()
print("BEFORE: compare", compatibility._window._comparison.label)
for index, (name, _text) in enumerate(rows):
    double_click(index)
print("OPENED fonts:", opened)
print("SOURCES:", [(item["label"], item["state"]) for item in c.w.sources.get()])
double_click(-1)
double_click(99)
print("LANDING left:", compatibility._window._landing)

# The Glyph Editor switches only after the window has redrawn the old glyph.
pending = []
sys.modules["mojo.UI"].OpenGlyphWindow = pending.append
current["glyph"] = FakeGlyph(paths["Regular"], "public.default", "B")
compatibility._window._comparison = next(s for s in c.session.sources if s.label == "Bold")
compatibility.refresh_open_window()
c._open_outline_row(types.SimpleNamespace(getNSTableView=lambda: Table(1)))
print("DELAYED before switch: compare", compatibility._window._comparison.label,
      "landing", compatibility._window._landing)
current["glyph"] = pending.pop()
compatibility.refresh_open_window()
print("DELAYED after switch: compare", compatibility._window._comparison.label,
      "landing", compatibility._window._landing)

# Contour order tab: cells of contours with issues are tinted red.
sys.modules["mojo.UI"].OpenGlyphWindow = open_glyph_window
for index in (0, 2):
    c._open_outline_row(types.SimpleNamespace(getNSTableView=lambda index=index: Table(index)))
    w = compatibility._window
    issue = compatibility._colours()["issue"]
    tinted = [tuple(round(v) for v in layer.getPosition())
              for layer in w.order.rows.getMerzContainer().getSublayers()
              if type(layer).__name__ == "Rectangle"
              and tuple(layer.getFillColor()) == tuple(issue)]
    print(f"TINTED {current['glyph'].name}: (x, y) of red cells", tinted)
