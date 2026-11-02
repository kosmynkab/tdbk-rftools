"""Drive the Points tab of the Compatibility window outside RoboFont.

Usage: python drive_points.py <lib path> [png path]
"""
import sys
import tempfile
import types
from pathlib import Path

lib = sys.argv[1]
png = sys.argv[2] if len(sys.argv) > 2 else None


def module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


sys.modules["mojo"] = None
import ezui  # noqa: E402,F401
import vanilla  # noqa: E402,F401
import merz  # noqa: E402,F401
del sys.modules["mojo"]
mojo = module("mojo")
mojo.__path__ = []
current = {"glyph": None}
module("mojo.UI", GetFile=lambda **k: None,
       CurrentGlyphWindow=lambda: (types.SimpleNamespace(getGlyph=lambda: current["glyph"])
                                   if current["glyph"] else None))
module("mojo.roboFont", AllFonts=lambda: [], CurrentGlyph=lambda: current["glyph"])

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


def square(x, size=100, reverse=False):
    points = [("line", x, 0), ("line", x + size, 0), ("line", x + size, size), ("line", x, size)]
    return points[:1] + points[:0:-1] if reverse else points


BOWL = [("line", 0, 0), ("line", 60, 0), (None, 100, 0), (None, 100, 100),
        ("curve", 60, 100), ("line", 0, 100)]

root = Path(tempfile.mkdtemp())
names = ["Regular", "Bold", "Light"] + [f"Extra{n}" for n in range(6)]
paths = {}
for index, name in enumerate(names):
    font = Font()
    if name == "Bold":
        draw(font.newGlyph("A"), square(200, 130), BOWL, square(400, reverse=True))
    elif name != "Light":                       # Light has no A
        draw(font.newGlyph("A"), BOWL, square(200), square(400))
    font.newGlyph("A").layer if name == "Light" else None
    paths[name] = root / f"{name}.ufo"
    font.save(str(paths[name]))
Font().save(str(root / "Other.ufo"))
document = DesignSpaceDocument()
axis = AxisDescriptor()
axis.name, axis.tag, axis.minimum, axis.default, axis.maximum = "Weight", "wght", 0, 0, 1000
document.addAxis(axis)
for index, name in enumerate(names):
    source = SourceDescriptor()
    source.path, source.name, source.location = str(paths[name]), name, {"Weight": index * 100}
    document.addSource(source)
designspace = root / "Test.designspace"
document.write(designspace)
if "Light" in names:   # make Light really lack A
    light = Font(str(paths["Light"]))
    if "A" in light:
        del light["A"]
        light.save()


class FakeGlyph:
    def __init__(self, path, layer, name):
        self.font = types.SimpleNamespace(path=str(path) if path else None)
        self.layer = types.SimpleNamespace(name=layer)
        self.name = name


FakeGlyph.contours = ()
FakeGlyph.__iter__ = lambda self: iter(self.contours)   # like DoodleGlyph: no .contours in RoboFont


def texts(view):
    return [layer.getText() for layer in view.getMerzContainer().getSublayers()
            if hasattr(layer, "getText")]


def colours_of(view, kind):
    return [layer.getStrokeColor() for layer in view.getMerzContainer().getSublayers()
            if type(layer).__name__ == kind]


compatibility.open_window()
window = compatibility._window
print("TAB on open:", window.w.tabs.get())
print("NO CLEANUP texts:", texts(window.points.drawing))
c = cleanup.open_window()
c.designspace_path = str(designspace)
c._load()

current["glyph"] = FakeGlyph(paths["Regular"], "public.default", "A")
compatibility.refresh_open_window()
print("REGULAR status:", window.w.status.get())
print("REGULAR texts:", texts(window.points.drawing))
buttons = lambda: {n: getattr(window.points, n).isEnabled() for n in ("matchDefault",)}
print("OLD buttons gone:", [n for n in ("setStart", "reverse") if hasattr(window.points, n)])
print("REGULAR buttons:", buttons())
print("BUTTON frames:", [getattr(window.points, n).getPosSize()
                         for n in ("matchDefault", "result")])

selected_glyph = FakeGlyph(paths["Bold"], "public.default", "A")
point = lambda on: types.SimpleNamespace(selected=on)
selected_glyph.contours = [[point(i == 1) for i in range(4)], [point(False)] * 6]
current["glyph"] = selected_glyph
compatibility.refresh_open_window()
print("BOLD texts:", texts(window.points.drawing))
print("BOLD buttons:", buttons())
lines = window.points.drawing.getMerzContainer().getSublayers()
print("BOLD sublayers:", len(lines), "view", window.points.drawing.width(),
      window.points.drawing.height())
from collections import Counter
print("POPUP items:", window.points.comparison.getItems(), "selected", window.points.comparison.get())
print("ARROWS enabled:", window.points.previous.isEnabled(), window.points.next.isEnabled())
print("BOLD line colours:", Counter(colours_of(window.points.drawing, "Line")))
print("BOLD oval colours:", Counter((tuple(l.getStrokeColor()), l.getSize()) for l in lines
                                    if type(l).__name__ == "Oval" and l.getSize()[0] >= 10))

def extent(view):
    xs = [l.getStartPoint()[0] for l in view.getMerzContainer().getSublayers()
          if type(l).__name__ == "Line"] + [l.getEndPoint()[0] for l in
          view.getMerzContainer().getSublayers() if type(l).__name__ == "Line"]
    return round(min(xs)), round(max(xs))
print("LINK x extent at", window.w.getPosSize()[2:], extent(window.points.drawing))
window.w.resize(1100, 700)
compatibility.refresh_open_window()
print("LINK x extent at", window.w.getPosSize()[2:], extent(window.points.drawing),
      "view", window.points.drawing.width(), window.points.drawing.height())
print("STROKE widths:", sorted({l.getStrokeWidth() for l in window.points.drawing.getMerzContainer().getSublayers()
                                if type(l).__name__ == "Line"}))
window._step_comparison(1)
print("NEXT ->", window._comparison.label, window.points.comparison.get(), texts(window.points.drawing))
window._step_comparison(-1); window._step_comparison(-1)
print("PREV PREV ->", window._comparison.label, window.points.comparison.get())
window.points.comparison.set(1)
window.choose_comparison(window.points.comparison)
print("POPUP pick ->", window._comparison.label, texts(window.points.drawing))
current["glyph"] = FakeGlyph(paths["Regular"], "public.default", "A")
compatibility.refresh_open_window()
print("SWITCH to Regular keeps:", window._comparison.label)
current["glyph"] = FakeGlyph(paths["Light"], "public.default", "A")
compatibility.refresh_open_window()
print("SWITCH to Light (was comparison) ->", window._comparison.label)
current["glyph"] = selected_glyph
compatibility.refresh_open_window()
window._comparison = None
compatibility.refresh_open_window()
print("BACK on Bold ->", window._comparison.label)
window.match_default(None)
print("MATCH DEFAULT result:", window.points.result.get())
print("MATCH DEFAULT saved Bold A:", [[(p.x, p.y) for p in c][:2] for c in Font(str(paths["Bold"]))["A"]])
window.match_default(None)
print("MATCH DEFAULT again:", window.points.result.get())
current["glyph"] = FakeGlyph(paths["Regular"], "public.default", "A")
compatibility.refresh_open_window()
print("OTHER GLYPH result cleared:", repr(window.points.result.get()))

if png:
    AppKit.NSApp().setAppearance_(AppKit.NSAppearance.appearanceNamed_(AppKit.NSAppearanceNameAqua))
    window.w.resize(900, 700)
    compatibility.refresh_open_window()
    view = window.points.drawing.getNSView()
    layer = view.layer()
    w, h = view.frame().size
    from Quartz import (CGBitmapContextCreate, CGBitmapContextCreateImage, CGColorSpaceCreateDeviceRGB,
                        kCGImageAlphaPremultipliedLast, CGContextSetRGBFillColor, CGContextFillRect)
    ctx = CGBitmapContextCreate(None, int(w), int(h), 8, 0, CGColorSpaceCreateDeviceRGB(),
                                kCGImageAlphaPremultipliedLast)
    CGContextSetRGBFillColor(ctx, 1, 1, 1, 1)
    CGContextFillRect(ctx, ((0, 0), (w, h)))
    layer.renderInContext_(ctx)
    rep = AppKit.NSBitmapImageRep.alloc().initWithCGImage_(CGBitmapContextCreateImage(ctx))
    rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, None).writeToFile_atomically_(png, True)
    print("PNG", png, w, h)

from tdbk_rftools.cleanup.outlines import Contour, Outline  # noqa: E402
from tdbk_rftools.cleanup.sources import Source  # noqa: E402
src = lambda label: Source(label, Path(label), None)
a, b, d = src("Cur"), src("Extra point"), src("Extra contour")
sq = Contour((("line", 0, 0), ("line", 100, 0), ("line", 100, 100), ("line", 0, 100)))
sq5 = Contour(sq.points[:2] + (("line", 100, 50),) + sq.points[2:])
window._draw_points(((a, Outline((sq,))), (b, Outline((sq5,)))), a, b, frozenset({(0, 2)}))
print("DIFF texts:", texts(window.points.drawing))
print("DIFF red rings:", sum(1 for l in window.points.drawing.getMerzContainer().getSublayers()
                            if type(l).__name__ == "Oval" and l.getSize()[0] == 14))
window._draw_points(((a, Outline((sq,))), (d, Outline((sq, sq)))), a, d, frozenset())
print("EXTRA CONTOUR texts:", texts(window.points.drawing))
window._draw_points(((a, Outline((sq,))),), a, None, frozenset())
print("ALONE texts:", texts(window.points.drawing))
