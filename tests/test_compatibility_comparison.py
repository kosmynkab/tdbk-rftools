from __future__ import annotations

import unittest
from pathlib import Path

from tdbk_rftools.cleanup.compatibility import comparison_choices, landing, pick_comparison
from tdbk_rftools.cleanup.outlines import Contour, Outline, OutlineRow
from tdbk_rftools.cleanup.sources import Source


def source(label):
    return Source(label, Path(f"/{label}.ufo"), None)


REGULAR, LIGHT, BOLD, BLACK = (source(label) for label in ("Regular", "Light", "Bold", "Black"))
SOURCES = (LIGHT, REGULAR, BOLD, BLACK)     # designspace order; Regular is the Default


class PickComparisonTests(unittest.TestCase):
    """The comparison source: the one other source the Points tab draws."""

    def test_the_default_source_comes_first(self):
        self.assertEqual(pick_comparison(SOURCES, BOLD, REGULAR, None), REGULAR)

    def test_from_the_default_source_the_first_other_source_in_designspace_order(self):
        self.assertEqual(pick_comparison(SOURCES, REGULAR, REGULAR, None), LIGHT)

    def test_the_comparison_source_stays_while_it_is_another_source(self):
        self.assertEqual(pick_comparison(SOURCES, LIGHT, REGULAR, BLACK), BLACK)
        self.assertEqual(pick_comparison(SOURCES, REGULAR, REGULAR, BLACK), BLACK)

    def test_editing_the_comparison_source_falls_back_to_the_default_first(self):
        self.assertEqual(pick_comparison(SOURCES, BOLD, REGULAR, BOLD), REGULAR)
        self.assertEqual(pick_comparison(SOURCES, REGULAR, REGULAR, REGULAR), LIGHT)

    def test_a_source_no_longer_in_the_designspace_is_not_kept(self):
        self.assertEqual(pick_comparison(SOURCES, BOLD, REGULAR, source("Gone")), REGULAR)

    def test_no_comparison_source_when_the_current_source_is_alone(self):
        self.assertIsNone(pick_comparison((REGULAR,), REGULAR, REGULAR, None))


SQUARE = Contour((("line", 0, 0), ("line", 100, 0), ("line", 100, 100), ("line", 0, 100)))
CLOCKWISE = Contour(SQUARE.points[:1] + SQUARE.points[:0:-1])   # runs the other way


class ComparisonChoicesTests(unittest.TestCase):
    """Every other source with its status, for the comparison source popup."""

    def test_each_other_source_in_designspace_order_with_its_status(self):
        outlines = ((LIGHT, Outline((SQUARE,))), (REGULAR, Outline((SQUARE,))),
                    (BOLD, Outline((CLOCKWISE,))), (BLACK, None))
        self.assertEqual(comparison_choices(outlines, REGULAR),
                         ((LIGHT, "compatible"), (BOLD, "2 wrong links"), (BLACK, "absent")))

    def test_no_choices_when_the_current_source_is_alone(self):
        self.assertEqual(comparison_choices(((REGULAR, Outline((SQUARE,))),), REGULAR), ())



def row(*kinds):
    """An Outlines list row: (source label, mismatch kinds) in designspace order."""
    return OutlineRow("a", "", tuple(kinds))


class LandingTests(unittest.TestCase):
    """Where a double-click in the Outlines list lands: the first mismatching
    source in the Glyph Editor, on the tab that fits the glyph's problem."""

    def test_contour_order_opens_the_contour_order_tab(self):
        self.assertEqual(landing(row(("Bold", ("contour order",)))), ("Bold", "Contour order"))

    def test_every_other_mismatch_opens_the_points_tab(self):
        for kinds in (("start point",), ("direction", "points"), ("open/closed",),
                      ("components",)):
            with self.subTest(kinds=kinds):
                self.assertEqual(landing(row(("Bold", kinds))), ("Bold", "Points"))

    def test_the_first_mismatching_source_opens_and_any_contour_problem_picks_the_tab(self):
        found = row(("Light", ("start point",)), ("Bold", ("contour count",)))
        self.assertEqual(landing(found), ("Light", "Contour order"))


if __name__ == "__main__":
    unittest.main()
