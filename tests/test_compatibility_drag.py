from __future__ import annotations

import unittest

from tdbk_rftools.cleanup.compatibility import CELL, GAP, LABELS, drag_order


def middle(cell):
    """The x of the middle of contour cell ``cell`` in a Contour order row."""
    return LABELS + cell * (CELL + GAP) + CELL / 2


class DragOrderTests(unittest.TestCase):
    def test_drag_first_contour_onto_the_last(self):
        self.assertEqual(drag_order(3, middle(0), middle(2)), (1, 2, 0))

    def test_letting_go_on_the_same_cell_changes_nothing(self):
        self.assertIsNone(drag_order(3, middle(1), middle(1) + 30))

    def test_letting_go_past_the_ends_moves_to_first_or_last(self):
        self.assertEqual(drag_order(3, middle(0), middle(9)), (1, 2, 0))
        self.assertEqual(drag_order(3, middle(2), 0), (2, 0, 1))
        self.assertEqual(drag_order(4, middle(3), middle(-1)), (3, 0, 1, 2))

    def test_pressing_outside_a_cell_drags_nothing(self):
        for press in (LABELS / 2,                  # source label
                      LABELS + CELL + GAP / 2,     # gap between cells 0 and 1
                      middle(3)):                  # past the last cell
            with self.subTest(press=press):
                self.assertIsNone(drag_order(3, press, middle(1)))


if __name__ == "__main__":
    unittest.main()
