"""Build the TDBK RFTools palette outside RoboFont and save a PNG of it.

Stubs only the mojo modules; ezui, vanilla and AppKit are RoboFont's real ones.
Usage: python render_palette.py <extension lib dir> <output.png>
"""
import sys
import types

lib, output = sys.argv[1], sys.argv[2]


def module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


class _Base:
    def __init__(self, *args, **kwargs):
        pass


# Import ezui with mojo absent so it takes its "not in RoboFont" fallbacks,
# then provide the stubs our own tool modules need.
sys.modules["mojo"] = None
import ezui  # noqa: E402,F401
del sys.modules["mojo"]

mojo = module("mojo")
mojo.__path__ = []
module("mojo.UI", inDarkMode=lambda: False, GetFile=lambda **k: None)
module("mojo.events", BaseEventTool=_Base, getActiveEventTool=lambda: None,
       installTool=lambda tool: None, uninstallTool=lambda tool: None,
       setActiveEventTool=lambda name: None)


class _Font:
    def __init__(self, family, style):
        self.info = types.SimpleNamespace(familyName=family, styleName=style)
        self.path = f"/tmp/{family}-{style}.ufo"


module("mojo.roboFont", AllFonts=lambda: [_Font("Amstelvar", "Regular"),
                                          _Font("Amstelvar", "Black")],
       CurrentGlyph=lambda: None, RGlyph=_Base)
module("mojo.subscriber", Subscriber=_Base,
       registerGlyphEditorSubscriber=lambda c: None,
       unregisterGlyphEditorSubscriber=lambda c: None,
       registerRoboFontSubscriber=lambda c: None,
       unregisterRoboFontSubscriber=lambda c: None)

sys.path.insert(0, lib)

import AppKit  # noqa: E402

AppKit.NSApplication.sharedApplication()

from tdbk_rftools.palette import TDBKRFToolsPaletteController  # noqa: E402

controller = TDBKRFToolsPaletteController()
window = controller.w.getNSWindow()
view = window.contentView()
view.layoutSubtreeIfNeeded()
frame = window.frame()
print(f"window size: {frame.size.width:.0f} x {frame.size.height:.0f}")
for identifier in ("cleanupButton",):
    item = controller.w.getItem(identifier)
    nsview = item.getNSView() if hasattr(item, "getNSView") else item._nsObject
    r = nsview.convertRect_toView_(nsview.bounds(), view)
    print(f"{identifier:24s} x={r.origin.x:5.0f} y={r.origin.y:5.0f} "
          f"w={r.size.width:5.0f} h={r.size.height:4.0f}")

window.display()
pdf = view.dataWithPDFInsideRect_(view.bounds())
pdf.writeToFile_atomically_(output.replace(".png", ".pdf"), True)


def walk(v, depth=0):
    text = ""
    if hasattr(v, "stringValue") and isinstance(v, AppKit.NSTextField):
        text = str(v.stringValue())
    elif isinstance(v, AppKit.NSButton):
        text = "[" + str(v.title()) + "]"
    if text:
        r = v.convertRect_toView_(v.bounds(), view)
        print(f"  {text!r:34s} x={r.origin.x:4.0f} y={r.origin.y:4.0f} w={r.size.width:4.0f}")
    for sub in v.subviews():
        walk(sub, depth + 1)


print("text items (y from bottom):")
walk(view)
