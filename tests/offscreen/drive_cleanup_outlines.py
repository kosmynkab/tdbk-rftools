"""Drive the Cleanup window outside RoboFont against closed test UFOs."""
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
module("mojo.UI", GetFile=lambda **k: None)
module("mojo.roboFont", AllFonts=lambda: [])

import AppKit  # noqa: E402
AppKit.NSApplication.sharedApplication()
sys.path.insert(0, lib)

from defcon import Font  # noqa: E402
from fontTools.designspaceLib import (  # noqa: E402
    AxisDescriptor, DesignSpaceDocument, SourceDescriptor,
)
from tdbk_rftools.cleanup.window import CleanupWindow  # noqa: E402




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


root = Path(tempfile.mkdtemp())
regular, bold = root / "Regular.ufo", root / "Bold.ufo"
font = Font()
for name in ("A", "B"):
    draw(font.newGlyph(name), square(0), square(200))
font.newGlyph("Z")
font.save(str(regular))
font = Font()
draw(font.newGlyph("A"), square(200, 130), square(0, 130))            # contour order
draw(font.newGlyph("B"), square(0, 130), square(200, 130, reverse=True))  # direction
font.save(str(bold))
document = DesignSpaceDocument()
axis = AxisDescriptor()
axis.name, axis.tag, axis.minimum, axis.default, axis.maximum = "Weight", "wght", 0, 0, 1000
document.addAxis(axis)
for name, path, weight in (("Regular", regular, 0), ("Bold", bold, 1000)):
    source = SourceDescriptor()
    source.path, source.name, source.location = str(path), name, {"Weight": weight}
    document.addSource(source)
designspace = root / "Test.designspace"
document.write(designspace)

window = CleanupWindow()
window.designspace_path = str(designspace)
window._load()
print("AUDIT:", [item["text"] for item in window.w.audit.get()])
print("OUTLINES:", [(item["glyph"], item["mismatches"]) for item in window.outlines.outlineRows.get()])
print("SUMMARY:", window.outlines.outlineSummary.get())
window.w.audit.setSelection([1])
window._audit_selected(window.w.audit)
print("TAB after outline line click:", window.w.sections.get())
window.w.audit.setSelection([0])
window._audit_selected(window.w.audit)
print("TAB after anchor line click:", window.w.sections.get())
for name in ("anchorRows", "matchDefault", "removeAll", "anchorSummary"):
    print("FRAME anchors", name, getattr(window.anchors, name)._nsObject.frame())
for name in ("outlineRows", "outlineSummary"):
    print("FRAME outlines", name, getattr(window.outlines, name)._nsObject.frame())
print("FRAME tabs", window.w.sections._nsObject.frame(), "marksTitle", window.w.marksTitle._nsObject.frame())
print("REPORT:", window.w.report.get())
