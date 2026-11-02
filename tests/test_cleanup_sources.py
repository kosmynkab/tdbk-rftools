from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from defcon import Font
from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor

from tdbk_rftools.cleanup.session import CleanupSession
from tdbk_rftools.cleanup.sources import Source, load_designspace


class LoadDesignspaceTests(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name).resolve()
        self.regular = self.root / "Regular.ufo"
        self.bold = self.root / "Bold.ufo"
        for path in (self.regular, self.bold):
            font = Font()
            font.newGlyph("A")
            font.save(str(path))
        document = DesignSpaceDocument()
        axis = AxisDescriptor()
        axis.name, axis.tag = "Weight", "wght"
        axis.minimum, axis.default, axis.maximum = 0, 0, 1000
        document.addAxis(axis)
        for name, path, weight, layer in (("Regular", self.regular, 0, None),
                                          ("Bold", self.bold, 1000, None),
                                          ("Medium", self.regular, 500, "medium")):
            source = SourceDescriptor()
            source.path, source.name = str(path), name
            source.location = {"Weight": weight}
            source.layerName = layer
            document.addSource(source)
        self.designspace = self.root / "Test.designspace"
        document.write(self.designspace)

    def tearDown(self):
        self._directory.cleanup()

    def test_default_and_layer_source(self):
        default, sources = load_designspace(self.designspace)
        self.assertEqual(default, Source("Regular", self.regular, None))
        self.assertEqual(sources, [
            Source("Regular", self.regular, None),
            Source("Bold", self.bold, None),
            Source("Medium [medium]", self.regular, "medium"),
        ])

    def test_default_override_must_be_a_full_source(self):
        default, _sources = load_designspace(self.designspace, self.bold)
        self.assertEqual(default.label, "Bold")
        with self.assertRaises(ValueError):
            load_designspace(self.designspace, self.root / "Other.ufo")

    def _anchors(self, path, glyph="A", layer=None):
        font = Font(str(path))
        target = font.layers[layer] if layer else font.layers.defaultLayer
        return [(a.name, a.x, a.y) for a in target[glyph].anchors]

    def _add(self, path, name, x, y, layer=None):
        font = Font(str(path))
        if layer and layer not in font.layers:
            font.newLayer(layer).newGlyph("A")
        target = font.layers[layer] if layer else font.layers.defaultLayer
        anchor = target["A"].instantiateAnchor()
        anchor.name, anchor.x, anchor.y = name, x, y
        target["A"].appendAnchor(anchor)
        font.save()

    def test_closed_sources_are_matched_and_saved_including_layer_sources(self):
        self._add(self.regular, "top", 100, 700)
        self._add(self.bold, "extra", 5, 5)
        self._add(self.regular, "top", 120, 690, layer="medium")
        self._add(self.regular, "ogonek", 1, 1, layer="medium")
        session = CleanupSession(*load_designspace(self.designspace), open_fonts=dict)
        report = session.anchor_report()
        self.assertEqual([row.glyph for row in report.rows], ["A"])
        self.assertEqual(report.rows[0].differences,
                         "Bold: missing top · extra extra · Medium [medium]: extra ogonek")
        saved, skipped, edits = session.match_default(["A"])
        self.assertEqual(saved, ("Bold", "Medium [medium]"))
        self.assertEqual(skipped, ())
        self.assertEqual(self._anchors(self.bold), [("top", 100, 700)])
        self.assertEqual(self._anchors(self.regular, layer="medium"), [("top", 120, 690)])
        self.assertEqual(session.anchor_report().rows, ())

    def test_remove_all_clears_the_default_too(self):
        self._add(self.regular, "top", 100, 700)
        self._add(self.bold, "top", 110, 700)
        session = CleanupSession(*load_designspace(self.designspace), open_fonts=dict)
        session.remove_all(["A"])
        self.assertEqual(session.warnings,
                         ("Medium [medium]: layer 'medium' not found; skipped",))
        self.assertEqual(self._anchors(self.regular), [])
        self.assertEqual(self._anchors(self.bold), [])


if __name__ == "__main__":
    unittest.main()
