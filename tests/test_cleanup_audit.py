from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from defcon import Font
from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor

from tdbk_rftools.cleanup.anchors import audit_anchors, issues
from tdbk_rftools.cleanup.audit import ufo_layers
from tdbk_rftools.cleanup.session import CleanupSession
from tdbk_rftools.cleanup.sources import load_designspace


class AnchorAuditTests(unittest.TestCase):
    def test_issue_kinds(self):
        default = [("top", 0, 0), ("bottom", 0, 0)]
        self.assertEqual(issues(default, default), set())
        self.assertEqual(issues(default, [("bottom", 0, 0), ("top", 0, 0)]), {"order"})
        self.assertEqual(issues(default, [("top", 0, 0), ("x", 0, 0)]), {"missing", "extra"})
        self.assertEqual(issues(default, [("top", 0, 0), ("top", 0, 0)]), {"duplicate"})

    def test_counts_glyphs_per_issue_and_source(self):
        default = {"A": [("top", 0, 0)], "B": [("top", 0, 0)], "C": [("a", 0, 0), ("a", 0, 0)]}
        others = {"Bold": {"A": [], "B": []}, "Light": {"A": []}}
        audit = audit_anchors(default, others)
        self.assertEqual(audit.glyphs["missing"], ("A", "B"))
        self.assertEqual(audit.sources["missing"], {"Bold": 2, "Light": 1})
        self.assertEqual(audit.glyphs["duplicate"], ("C",))
        self.assertEqual(audit.sources["duplicate"], {"default": 1})

    def test_layers_skip_main_and_layer_sources_and_split_background(self):
        summary = ufo_layers("Regular", [("public.default", 300), ("medium", 20),
                                         ("public.background", 12), ("sketch", 4)],
                             "public.default", {"medium"})
        self.assertEqual(summary.extra, (("sketch", 4),))
        self.assertEqual(summary.background, 12)


class SessionAuditTests(unittest.TestCase):
    def test_audit_reads_layers_guides_colours_and_anchors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            regular, bold = root / "Regular.ufo", root / "Bold.ufo"
            font = Font()
            glyph = font.newGlyph("A")
            anchor = glyph.instantiateAnchor()
            anchor.name, anchor.x, anchor.y = "top", 1, 2
            glyph.appendAnchor(anchor)
            glyph.markColor = "1,0,0,1"
            glyph.appendGuideline({"x": 10})
            glyph.appendGuideline({"y": 500})
            font.appendGuideline({"y": 700})
            font.newLayer("sketch").newGlyph("A")
            font.save(str(regular))
            other = Font()
            other.newGlyph("A")
            other.save(str(bold))
            document = DesignSpaceDocument()
            axis = AxisDescriptor()
            axis.name, axis.tag = "Weight", "wght"
            axis.minimum, axis.default, axis.maximum = 0, 0, 1000
            document.addAxis(axis)
            for name, path, weight in (("Regular", regular, 0), ("Bold", bold, 1000)):
                source = SourceDescriptor()
                source.path, source.name, source.location = str(path), name, {"Weight": weight}
                document.addSource(source)
            designspace = root / "Test.designspace"
            document.write(designspace)
            audit = CleanupSession(*load_designspace(designspace), open_fonts=dict).audit()
            lines = [line.text for line in audit.lines()]
            self.assertEqual(lines, [
                "Anchors · missing anchors: 1 glyph (Bold 1)",
                "Outlines · compatible",
                "Layers · Regular: sketch (1)",
                "Guides · Regular: 1 glyph / 2 guides · 1 font guides",
                "Mark colours · Regular 1",
            ])
            self.assertEqual(audit.lines()[0].issue, "missing")


if __name__ == "__main__":
    unittest.main()
