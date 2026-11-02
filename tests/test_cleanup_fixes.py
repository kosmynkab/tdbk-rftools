from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from defcon import Font
from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor

from tdbk_rftools.cleanup.anchors import find_differences
from tdbk_rftools.cleanup.session import CleanupSession
from tdbk_rftools.cleanup.sources import load_designspace


class AbsentBySourceTests(unittest.TestCase):
    def test_lists_missing_default_glyphs_per_source(self):
        default = {"A": [], "B": [], "C": []}
        others = {"Bold": {"A": []}, "Light": {"A": [], "B": [], "C": []},
                  "Black": {"C": [], "Z": []}}
        report = find_differences(default, others)
        self.assertEqual(report.absent_by_source,
                         (("Bold", ("B", "C")), ("Black", ("A", "B"))))
        self.assertEqual(report.absent, ("A", "B", "C"))


class FixTests(unittest.TestCase):
    """Regular (default, with a 'medium' layer-source) + Bold, all closed."""

    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        root = Path(self._directory.name).resolve()
        self.regular, self.bold = root / "Regular.ufo", root / "Bold.ufo"
        font = Font()
        for name in ("A", "B"):
            glyph = font.newGlyph(name)
            glyph.markColor = "1,0,0,1"
            glyph.appendGuideline({"x": 10, "name": "g"})
        font.appendGuideline({"y": 700, "name": "f"})
        font.newLayer("medium").newGlyph("A").markColor = "0,1,0,1"
        font.newLayer("sketch").newGlyph("A")
        font.newLayer("public.background").newGlyph("B")
        font.save(str(self.regular))
        font = Font()
        font.newGlyph("A").appendGuideline({"y": 5, "name": "g"})
        font.newLayer("old").newGlyph("A")
        font.save(str(self.bold))

        document = DesignSpaceDocument()
        axis = AxisDescriptor()
        axis.name, axis.tag = "Weight", "wght"
        axis.minimum, axis.default, axis.maximum = 0, 0, 1000
        document.addAxis(axis)
        for name, path, weight, layer in (("Regular", self.regular, 0, None),
                                          ("Medium", self.regular, 500, "medium"),
                                          ("Bold", self.bold, 1000, None)):
            source = SourceDescriptor()
            source.path, source.name, source.location = str(path), name, {"Weight": weight}
            source.layerName = layer
            document.addSource(source)
        self.designspace = root / "Test.designspace"
        document.write(self.designspace)
        self.session = CleanupSession(*load_designspace(self.designspace), open_fonts=dict)

    def tearDown(self):
        self._directory.cleanup()

    def test_remove_extra_layers_keeps_main_and_layer_sources(self):
        result = self.session.remove_extra_layers()
        self.assertEqual(result.removed, (("Regular", "sketch", 1),
                                          ("Regular", "public.background", 1),
                                          ("Bold", "old", 1)))
        self.assertEqual(result.saved, ("Bold", "Regular"))
        self.assertEqual(Font(str(self.regular)).layers.layerOrder,
                         ["public.default", "medium"])
        self.assertEqual(Font(str(self.bold)).layers.layerOrder, ["public.default"])
        self.assertEqual(self.session.remove_extra_layers().removed, ())

    def test_remove_guides_clears_glyph_and_font_guides(self):
        result = self.session.remove_guides()
        self.assertEqual(result.removed, (("Regular", "glyph guides", 2),
                                          ("Regular", "font guides", 1),
                                          ("Bold", "glyph guides", 1)))
        regular = Font(str(self.regular))
        self.assertEqual(regular.guidelines, [])
        self.assertEqual([g.guidelines for g in regular], [[], []])
        self.assertEqual(Font(str(self.bold))["A"].guidelines, [])

    def test_strip_mark_colours_in_every_source_layer(self):
        result = self.session.strip_mark_colours()
        self.assertEqual(result.removed, (("Regular", "mark colours", 2),
                                          ("Medium [medium]", "mark colours", 1)))
        self.assertEqual(result.saved, ("Medium [medium]", "Regular"))
        regular = Font(str(self.regular))
        self.assertEqual([g.markColor for g in regular], [None, None])
        self.assertIsNone(regular.layers["medium"]["A"].markColor)
        lines = [line.text for line in self.session.audit().lines()]
        self.assertIn("Mark colours · none", lines)


class _OpenGlyph:
    """Stands in for a RoboFont glyph: records undo titles and changed()."""

    def __init__(self, glyph, log):
        self._glyph, self._log = glyph, log

    def naked(self):
        return self._glyph

    def undo(self, title):
        log, name = self._log, self._glyph.name

        class Undo:
            def __enter__(self):
                log.append(("undo", name, title))

            def __exit__(self, *exc):
                return False
        return Undo()

    def changed(self):
        self._log.append(("changed", self._glyph.name))


class _OpenFont:
    """Stands in for a RoboFont font open in the app, wrapping a defcon font."""

    def __init__(self, path):
        self._font, self.log = Font(str(path)), []
        self.defaultLayerName = self._font.layers.defaultLayer.name

    def naked(self):
        return self._font

    def getLayer(self, name):
        layer, log = self._font.layers[name], self.log

        class Layer:
            def __getitem__(self, glyph_name):
                return _OpenGlyph(layer[glyph_name], log)
        return Layer()

    def removeLayer(self, name):
        del self._font.layers[name]

    def clearGuidelines(self):
        self._font.clearGuidelines()


class OpenFontFixTests(FixTests):
    """Regular is open in RoboFont: changed in place with undo, never saved."""

    def setUp(self):
        super().setUp()
        self.open = _OpenFont(self.regular)
        fonts = {self.regular: self.open}
        self.session = CleanupSession(*load_designspace(self.designspace),
                                      open_fonts=lambda: fonts)

    def _on_disk_unchanged(self):
        regular = Font(str(self.regular))
        self.assertEqual(regular["A"].markColor, "1,0,0,1")
        self.assertEqual(len(regular["A"].guidelines), 1)
        self.assertEqual(len(regular.guidelines), 1)

    def test_remove_extra_layers_keeps_main_and_layer_sources(self):
        result = self.session.remove_extra_layers()
        self.assertEqual(result.removed, (("Regular", "sketch", 1),
                                          ("Regular", "public.background", 1),
                                          ("Bold", "old", 1)))
        self.assertEqual(result.saved, ("Bold",))
        self.assertEqual(result.no_undo, ("Regular",))
        self.assertEqual(self.open.naked().layers.layerOrder, ["public.default", "medium"])
        self.assertEqual(len(Font(str(self.regular)).layers), 4)

    def test_remove_guides_clears_glyph_and_font_guides(self):
        result = self.session.remove_guides()
        self.assertEqual(result.removed, (("Regular", "glyph guides", 2),
                                          ("Regular", "font guides", 1),
                                          ("Bold", "glyph guides", 1)))
        self.assertEqual(result.saved, ("Bold",))
        self.assertEqual(result.no_undo, ("Regular",))
        font = self.open.naked()
        self.assertEqual(font.guidelines, [])
        self.assertEqual([g.guidelines for g in font], [[], []])
        self.assertCountEqual(self.open.log, [("undo", "A", "Remove Guides"), ("changed", "A"),
                                              ("undo", "B", "Remove Guides"), ("changed", "B")])
        self.assertEqual(Font(str(self.bold))["A"].guidelines, [])
        self._on_disk_unchanged()

    def test_strip_mark_colours_in_every_source_layer(self):
        result = self.session.strip_mark_colours()
        self.assertEqual(result.removed, (("Regular", "mark colours", 2),
                                          ("Medium [medium]", "mark colours", 1)))
        self.assertEqual(result.saved, ())
        self.assertEqual(result.no_undo, ())
        font = self.open.naked()
        self.assertEqual([g.markColor for g in font], [None, None])
        self.assertIsNone(font.layers["medium"]["A"].markColor)
        self.assertIn(("undo", "A", "Strip Mark Colours"), self.open.log)
        self._on_disk_unchanged()

    def test_anchor_fixes_change_open_fonts_with_undo(self):
        anchor = self.open.naked()["A"].instantiateAnchor()
        anchor.name, anchor.x, anchor.y = "top", 100, 700
        self.open.naked()["A"].appendAnchor(anchor)
        saved, skipped, _edits = self.session.match_default(["A"])
        self.assertEqual((saved, skipped), (("Bold",), ()))
        self.assertEqual([(a.name, a.x, a.y) for a in Font(str(self.bold))["A"].anchors],
                         [("top", 100, 700)])
        medium = self.open.naked().layers["medium"]["A"]
        self.assertEqual([(a.name, a.x, a.y) for a in medium.anchors], [("top", 100, 700)])
        self.assertIn(("undo", "A", "Match Default Anchors"), self.open.log)
        saved, _skipped, _edits = self.session.remove_all(["A"])
        self.assertEqual(saved, ("Bold",))
        self.assertEqual(self.open.naked()["A"].anchors, [])
        self.assertEqual(medium.anchors, [])
        self.assertIn(("undo", "A", "Remove All Anchors"), self.open.log)
        self.assertEqual(Font(str(self.regular))["A"].anchors, [])


if __name__ == "__main__":
    unittest.main()
