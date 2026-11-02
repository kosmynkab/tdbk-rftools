from __future__ import annotations

import unittest

from defcon import Font

from tdbk_rftools.cleanup.anchors import (
    GlyphEdit, apply_edit, find_differences, plan_match_default, plan_remove_all,
)


def records(glyph):
    return [(anchor.name, anchor.x, anchor.y) for anchor in glyph.anchors]


def add(glyph, name, x, y):
    anchor = glyph.instantiateAnchor()
    anchor.name, anchor.x, anchor.y = name, x, y
    glyph.appendAnchor(anchor)


DEFAULT = {
    "A": [("top", 100, 700), ("bottom", 100, 0)],
    "B": [("top", 50, 700)],
    "C": [],
    "D": [("top", 1, 1)],
}


class FindDifferencesTests(unittest.TestCase):
    def test_lists_missing_extra_order_and_duplicates_per_source(self):
        others = {
            "Bold": {
                "A": [("bottom", 120, 0), ("top", 130, 720)],   # order only
                "B": [("top", 60, 720), ("_top", 1, 2)],        # extra
                "C": [("ogonek", 3, 4)],                        # extra vs empty default
                "D": [("top", 1, 1)],                           # same
            },
            "Light": {
                "A": [("top", 90, 690)],                        # missing bottom
                "B": [("top", 1, 2), ("top", 3, 4)],            # duplicate
            },
        }
        report = find_differences(DEFAULT, others)
        rows = {row.glyph: row for row in report.rows}
        self.assertEqual(sorted(rows), ["A", "B", "C"])
        self.assertEqual(rows["A"].differences,
                         "Bold: order · Light: missing bottom")
        self.assertEqual(rows["B"].differences,
                         "Bold: extra _top · Light: duplicate top")
        self.assertTrue(rows["B"].duplicates)
        self.assertFalse(rows["A"].duplicates)
        self.assertEqual(rows["C"].differences, "Bold: extra ogonek")

    def test_counts_absent_and_outside_default_glyphs_without_rows(self):
        others = {
            "Bold": {"A": DEFAULT["A"], "B": DEFAULT["B"], "Z": []},
            "Sparse": {"A": DEFAULT["A"], "Y": [("top", 0, 0)]},
        }
        report = find_differences(DEFAULT, others)
        self.assertEqual(report.rows, ())
        self.assertEqual(report.absent, ("B", "C", "D"))
        self.assertEqual(report.outside_default, ("Y", "Z"))

    def test_duplicate_in_default_is_flagged(self):
        default = {"A": [("top", 1, 1), ("top", 2, 2)]}
        report = find_differences(default, {"Bold": {"A": [("top", 1, 1)]}})
        self.assertEqual(report.rows[0].differences, "default: duplicate top")
        self.assertTrue(report.rows[0].duplicates)


class PlanTests(unittest.TestCase):
    OTHERS = {
        "Bold": {
            "A": [("bottom", 120, 0), ("extra", 9, 9)],
            "B": [("top", 1, 2), ("top", 3, 4)],
            "D": [("top", 1, 1)],
        },
        "Light": {"A": [("top", 90, 690), ("bottom", 90, 0)]},
    }

    def test_match_default_targets_default_names_and_skips_duplicates(self):
        edits, skipped = plan_match_default(DEFAULT, self.OTHERS, ["A", "B", "D"])
        self.assertEqual(skipped, ("B",))
        self.assertEqual(edits, (
            GlyphEdit("Bold", "A", (("top", 100, 700), ("bottom", 100, 0)), ("top",)),
        ))

    def test_remove_all_covers_every_source_including_default(self):
        edits = plan_remove_all("Regular", DEFAULT, self.OTHERS, ["A", "B"])
        self.assertEqual(
            sorted((edit.source, edit.glyph) for edit in edits),
            [("Bold", "A"), ("Bold", "B"), ("Light", "A"),
             ("Regular", "A"), ("Regular", "B")])
        self.assertTrue(all(edit.target == () for edit in edits))


class ApplyEditTests(unittest.TestCase):
    def test_match_keeps_positions_adds_at_default_and_orders(self):
        glyph = Font().newGlyph("A")
        add(glyph, "extra", 9, 10)
        add(glyph, "bottom", 120, -5)
        apply_edit(glyph, GlyphEdit("Bold", "A",
                                    (("top", 100, 700), ("bottom", 100, 0)), ("top",)))
        self.assertEqual(records(glyph), [("top", 100, 700), ("bottom", 120, -5)])

    def test_remove_all(self):
        glyph = Font().newGlyph("A")
        add(glyph, "top", 1, 2)
        add(glyph, "top", 3, 4)
        apply_edit(glyph, GlyphEdit("Bold", "A", (), ()))
        self.assertEqual(records(glyph), [])


if __name__ == "__main__":
    unittest.main()
