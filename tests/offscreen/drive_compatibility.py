"""Drive the Compatibility window outside RoboFont against closed test UFOs.

Usage: python drive_compatibility.py <lib path> [png path]
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
    """Shaped like RoboFont's DoodleGlyph: iterate it for contours."""
    contours = ()

    def __iter__(self):
        return iter(self.contours)

    def __init__(self, path, layer, name):
        self.font = types.SimpleNamespace(path=str(path) if path else None)
        self.layer = types.SimpleNamespace(name=layer)
        self.name = name


def state(title):
    window = compatibility._window
    rows = window.order.rows
    container = rows.getMerzContainer()
    print(f"[{title}] status={window.w.status.get()!r} "
          f"openCleanup visible={window.w.openCleanup.isVisible()} "
          f"sublayers={len(container.getSublayers())} doc={rows.getMerzViewSize()} "
          f"visible={rows.getSize()} tab={window.w.tabs.get()}")


compatibility.open_window()
compatibility._window.w.tabs.set(1)     # the window opens on Points
state("no cleanup")
c = cleanup.open_window()
c.designspace_path = str(designspace)
c._load()
state("cleanup loaded, no glyph")
current["glyph"] = FakeGlyph(root / "Other.ufo", "foreground", "A")
compatibility.refresh_open_window()
state("not a source")
current["glyph"] = FakeGlyph(paths["Regular"], "background", "A")
compatibility.refresh_open_window()
state("source UFO, wrong layer")
current["glyph"] = FakeGlyph(paths["Bold"], "public.default", "A")
compatibility.refresh_open_window()
state("Bold A")
_c = compatibility._window.order.rows.getMerzView().getNSView()
_b = _c.superview().bounds()
print("TOP gap on first tall draw:", round(_c.frame().size.height - (_b.origin.y + _b.size.height)))
texts = [layer.getText() for layer in compatibility._window.order.rows.getMerzContainer().getSublayers()
         if hasattr(layer, "getText")]
print("TEXTS:", texts)
order = compatibility._window.order
print("MATCH enabled", order.matchOrder.isEnabled(), "frames", order.matchOrder._nsObject.frame(),
      order.result._nsObject.frame(), order.rows._nsObject.frame())
order.matchOrder._nsObject.performClick_(None)
print("MATCH result:", order.result.get())
print("BOLD A on disk:", [len(contour) for contour in Font(str(paths["Bold"]))["A"]])
order.matchOrder._nsObject.performClick_(None)
print("MATCH again:", order.result.get())


def mouse(kind, x, y):
    """Send a real mouse event at merz view point (x, y)."""
    view = compatibility._window.order.rows.getMerzView().getNSView()
    location = view.convertPoint_toView_((x, y), None)
    types_ = {"down": AppKit.NSEventTypeLeftMouseDown, "drag": AppKit.NSEventTypeLeftMouseDragged,
              "up": AppKit.NSEventTypeLeftMouseUp}
    event = AppKit.NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
        types_[kind], location, 0, 0, view.window().windowNumber(), None, 0, 1, 1)
    view.window().sendEvent_(event)     # through AppKit's hit testing, like a real click


def cell_x(cell):
    return compatibility.LABELS + cell * (compatibility.CELL + compatibility.GAP) + compatibility.CELL / 2


def row_y(row):
    height = compatibility._window._drawn[3]
    return height - compatibility.PAD - row * compatibility.ROW - compatibility.CELL / 2


def disk(name):
    return [len(contour) for contour in Font(str(paths[name]))["A"]]


_v = compatibility._window.order.rows.getMerzView().getNSView()
_v.scrollPoint_((0, _v.frame().size.height))
_loc = _v.convertPoint_toView_((cell_x(0), row_y(1)), None)
_hit = _v.window().contentView().superview().hitTest_(_loc) if _v.window().contentView().superview() else None
_v = compatibility._window.order.rows.getMerzView().getNSView()


def top_gap():
    """Points between the document top and the top of the visible part."""
    visible = _v.superview().bounds()       # the clip view
    return round(_v.frame().size.height - (visible.origin.y + visible.size.height))


print("TOP gap on open:", top_gap())
_v.scrollPoint_((0, 300))
gap = top_gap()
compatibility.refresh_open_window()
print("TOP gap kept on redraw:", gap, "->", top_gap())
_v.scrollPoint_((0, _v.frame().size.height))
print("SECOND rows view (extension reload):", compatibility._rows_view((0, 0, 100, 100), None))
print("DRAG before: Bold", disk("Bold"), "Regular", disk("Regular"))
mouse("down", cell_x(0), row_y(1))          # Bold, first contour
mouse("drag", cell_x(1), row_y(1))
preview = [layer.getText() for layer in compatibility._window.order.rows.getMerzContainer().getSublayers()
           if hasattr(layer, "getText")]
print("DRAG preview texts:", preview)
mouse("drag", cell_x(2), row_y(3))          # wander into another row
compatibility.refresh_open_window()          # a redraw mid-drag must not cancel it
mouse("up", cell_x(2), row_y(3))
print("DRAG result:", compatibility._window.order.result.get())
print("DRAG after: Bold", disk("Bold"), "Regular", disk("Regular"))
mouse("down", cell_x(1), row_y(1))
mouse("up", cell_x(1) + 20, row_y(1))       # same cell: nothing
print("DRAG same cell after: Bold", disk("Bold"), "result", compatibility._window.order.result.get())
mouse("down", cell_x(0), row_y(2))          # Light has no A
mouse("up", cell_x(2), row_y(2))
print("DRAG absent row: Light A?", "A" in Font(str(paths["Light"])))
mouse("down", 20, row_y(1))                 # label column
mouse("up", cell_x(2), row_y(1))
print("DRAG label press: Bold", disk("Bold"))

current["glyph"] = FakeGlyph(None, "foreground", "A")
compatibility.refresh_open_window()
state("unsaved font")
current["glyph"] = FakeGlyph(paths["Bold"], "public.default", "A")
print("FRAMES status", compatibility._window.w.status._nsObject.frame(),
      "tabs", compatibility._window.w.tabs._nsObject.frame())
print("CLEANUP compat button", c.outlines.compatibility._nsObject.frame(),
      "summary", c.outlines.outlineSummary._nsObject.frame())
c.w.close()
state("cleanup closed")

if png:
    current["glyph"] = FakeGlyph(paths["Bold"], None, "A")
    c = cleanup.open_window()
    c.designspace_path = str(designspace)
    c._load()
    view = compatibility._window.order.rows.getMerzView().getNSView()
    layer = view.layer()
    w, h = view.frame().size
    from Quartz import (CGBitmapContextCreate, CGBitmapContextCreateImage, CGColorSpaceCreateDeviceRGB,
                        kCGImageAlphaPremultipliedLast)
    ctx = CGBitmapContextCreate(None, int(w), int(h), 8, 0, CGColorSpaceCreateDeviceRGB(),
                                kCGImageAlphaPremultipliedLast)
    from Quartz import CGContextSetRGBFillColor, CGContextFillRect
    CGContextSetRGBFillColor(ctx, 1, 1, 1, 1)
    CGContextFillRect(ctx, ((0, 0), (w, h)))
    layer.renderInContext_(ctx)
    image = CGBitmapContextCreateImage(ctx)
    rep = AppKit.NSBitmapImageRep.alloc().initWithCGImage_(image)
    rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, None).writeToFile_atomically_(png, True)
    print("PNG", png, w, h)
