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


def anchor(glyph, name, x, y):
    a = glyph.instantiateAnchor()
    a.name, a.x, a.y = name, x, y
    glyph.appendAnchor(a)


root = Path(tempfile.mkdtemp())
regular, bold = root / "Regular.ufo", root / "Bold.ufo"
font = Font()
for name in ("A", "B", "C"):
    glyph = font.newGlyph(name)
    anchor(glyph, "top", 100, 700)
    anchor(glyph, "bottom", 100, 0)
font["A"].markColor = "1,0,0,1"
font.newLayer("sketch").newGlyph("A")
font.save(str(regular))
font = Font()
anchor(font.newGlyph("A"), "top", 120, 720)                       # missing bottom
glyph = font.newGlyph("B")
anchor(glyph, "bottom", 1, 1)
anchor(glyph, "top", 2, 2)                                        # order only
glyph = font.newGlyph("C")
anchor(glyph, "top", 1, 1)
anchor(glyph, "top", 2, 2)                                        # duplicate
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
print("SOURCES:", [(item["label"], item["state"]) for item in window.w.sources.get()])
print("AUDIT:")
for item in window.w.audit.get():
    print("  ", item["text"])
print("ROWS:", [(item["glyph"], item["differences"]) for item in window.anchors.anchorRows.get()])

window.w.audit.setSelection([0])            # first audit line
window._audit_selected(window.w.audit)
selected = [window._rows[i].glyph for i in window.anchors.anchorRows.getSelection()]
print("AUDIT LINE 0 SELECTS:", selected)

window.anchors.anchorRows.setSelection(list(range(len(window._rows))))
window.match_default(None)
print("REPORT:\n" + window.w.report.get())
print("ROWS AFTER:", [(item["glyph"], item["differences"]) for item in window.anchors.anchorRows.get()])
saved = Font(str(bold))
print("BOLD ON DISK:", {n: [(a.name, a.x, a.y) for a in saved[n].anchors] for n in "ABC"})
