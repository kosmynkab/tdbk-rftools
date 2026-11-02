from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from defcon import Font
from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor

from tdbk_rftools.cleanup.outlines import (
    Contour, ContourFix, Outline, contour_issues, describe, links, mismatches, plan_contours, plan_order,
)
from tdbk_rftools.cleanup.session import CleanupSession
from tdbk_rftools.cleanup.sources import load_designspace


def square(x=0, y=0, size=100, start=0, reverse=False):
    """A closed counter-clockwise square of line points, starting bottom left."""
    points = [("line", x, y), ("line", x + size, y),
              ("line", x + size, y + size), ("line", x, y + size)]
    if reverse:
        points = points[:1] + points[:0:-1]
    points = points[start:] + points[:start]
    return Contour(tuple(points))


# A counter-clockwise "D": two lines, a curve, a line, closing with a line.
D = Contour((("line", 0, 0), ("line", 60, 0), ("offcurve", 100, 0),
             ("offcurve", 100, 100), ("curve", 60, 100), ("line", 0, 100)))


# The same "D" drawn clockwise, starting at the same corner.
D_CLOCKWISE = Contour((("line", 0, 0), ("line", 0, 100), ("line", 60, 100),
                       ("offcurve", 100, 100), ("offcurve", 100, 0), ("curve", 60, 0)))


# A counter-clockwise stadium: line, curve, line, curve. Point types fit two
# start points, half a turn apart.
STADIUM = Contour((("line", 0, 0), ("offcurve", 40, -30), ("offcurve", 80, -30),
                   ("curve", 120, 0), ("line", 120, 100), ("offcurve", 80, 130),
                   ("offcurve", 40, 130), ("curve", 0, 100)))
# The same stadium drawn clockwise from the top left corner.
STADIUM_CLOCKWISE = Contour((("line", 0, 100), ("offcurve", 40, 130), ("offcurve", 80, 130),
                             ("curve", 120, 100), ("line", 120, 0), ("offcurve", 80, -30),
                             ("offcurve", 40, -30), ("curve", 0, 0)))


def turn(contour, start):
    """The same contour starting at point ``start``."""
    return Contour(contour.points[start:] + contour.points[:start], contour.closed)


def bolder(contour):
    """A heavier copy: every coordinate scaled, so positions differ."""
    return Contour(tuple((kind, x * 1.4 + 7, y * 1.2) for kind, x, y in contour.points),
                   contour.closed)


class MismatchTests(unittest.TestCase):
    def test_same_outline_is_compatible(self):
        glyph = Outline((square(), square(200)))
        self.assertEqual(mismatches(glyph, glyph), set())

    def test_contour_count(self):
        self.assertEqual(mismatches(Outline((square(), square(200))), Outline((square(),))),
                         {"contour count"})

    def test_start_point_in_a_bolder_source(self):
        self.assertEqual(mismatches(Outline((D,)), Outline((turn(bolder(D), 1),))),
                         {"start point"})

    def test_a_start_point_point_types_cannot_tell_apart_is_no_mismatch(self):
        # Every corner of a square is a line point: types allow any start.
        self.assertEqual(mismatches(Outline((square(),)), Outline((square(size=140, start=1),))),
                         set())

    def test_direction(self):
        self.assertEqual(mismatches(Outline((square(),)), Outline((square(reverse=True),))),
                         {"direction"})

    def test_direction_and_start_point(self):
        self.assertEqual(mismatches(Outline((D,)), Outline((turn(D_CLOCKWISE, 1),))),
                         {"direction", "start point"})

    def test_direction_of_a_curved_contour(self):
        self.assertEqual(mismatches(Outline((D,)), Outline((D_CLOCKWISE,))), {"direction"})

    def test_point_count_and_types(self):
        extra = Contour(D.points[:1] + (("line", 30, 0),) + D.points[1:])
        self.assertEqual(mismatches(Outline((D,)), Outline((extra,))), {"points"})
        curved = Contour((("curve", 0, 0),) + D.points[1:])
        self.assertEqual(mismatches(Outline((D,)), Outline((curved,))), {"points"})

    def test_open_vs_closed(self):
        open_line = Contour((("move", 0, 0), ("line", 100, 0)), closed=False)
        closed_line = Contour((("line", 0, 0), ("line", 100, 0)))
        self.assertEqual(mismatches(Outline((open_line,)), Outline((closed_line,))),
                         {"open/closed"})

    def test_open_contour_direction(self):
        forward = Contour((("move", 0, 0), ("offcurve", 10, 50), ("offcurve", 90, 50),
                           ("curve", 100, 0), ("line", 200, 0)), closed=False)
        backward = Contour((("move", 200, 0), ("line", 100, 0), ("offcurve", 90, 50),
                            ("offcurve", 10, 50), ("curve", 0, 0)), closed=False)
        self.assertEqual(mismatches(Outline((forward,)), Outline((forward,))), set())
        self.assertEqual(mismatches(Outline((forward,)), Outline((backward,))), {"direction"})

    def test_a_start_point_point_types_cannot_tell_is_still_a_start_point_mismatch(self):
        # The types prove the start is wrong, even if they can't say which is right.
        self.assertEqual(mismatches(Outline((STADIUM,)), Outline((turn(STADIUM, 3),))),
                         {"start point"})

    def test_contour_order(self):
        self.assertEqual(mismatches(Outline((D, square(200))), Outline((square(200), D))),
                         {"contour order"})

    def test_position_breaks_ties_between_contours_of_the_same_structure(self):
        # A colon: two dots, the second source a bolder copy.
        default = Outline((square(0, 0, 50), square(0, 300, 50)))
        self.assertEqual(mismatches(default, Outline((square(0, 0, 70), square(0, 310, 70)))),
                         set())
        self.assertEqual(mismatches(default, Outline((square(0, 310, 70), square(0, 0, 70)))),
                         {"contour order"})

    def test_contour_order_with_direction_inside(self):
        other = Outline((square(200, reverse=True), D))
        self.assertEqual(mismatches(Outline((D, square(200))), other),
                         {"contour order", "direction"})

    def test_components(self):
        self.assertEqual(mismatches(Outline(components=("A", "acute")),
                                    Outline(components=("A",))), {"components"})
        self.assertEqual(mismatches(Outline(components=("A", "acute")),
                                    Outline(components=("A", "grave"))), {"components"})


class PlanOrderTests(unittest.TestCase):
    """The contour order that makes a source match the Default source."""

    def test_order_puts_each_contour_under_its_default_partner(self):
        plan = plan_order((D, square(200), square(400, size=50)),
                          (square(400, size=50), D, square(200)))
        self.assertEqual((plan.order, plan.reason), ((1, 2, 0), ""))

    def test_order_ignores_start_point_and_direction(self):
        plan = plan_order((D, square(200)), (square(200, reverse=True, start=2), D))
        self.assertEqual(plan.order, (1, 0))

    def test_position_breaks_ties_between_contours_of_the_same_structure(self):
        # A colon in a bolder source, dots listed top first.
        plan = plan_order((square(0, 0, 50), square(0, 300, 50)),
                          (square(0, 310, 70), square(0, 0, 70)))
        self.assertEqual(plan.order, (1, 0))

    def test_already_in_order(self):
        self.assertEqual(plan_order((D, square(200)), (D, square(200))).order, (0, 1))

    def test_refuses_when_contour_counts_differ(self):
        plan = plan_order((D, square(200)), (D,))
        self.assertIsNone(plan.order)
        self.assertEqual(plan.reason, "1 contour, the Default source has 2")

    def test_refuses_when_no_order_lines_up(self):
        extra = Contour(D.points[:1] + (("line", 30, 0),) + D.points[1:])
        plan = plan_order((D, square(200)), (square(200), extra))
        self.assertIsNone(plan.order)
        self.assertEqual(plan.reason, "contours differ in points from the Default source")

    def test_open_and_closed_contours_are_never_swapped(self):
        line = Contour((("move", 0, 0), ("line", 100, 0), ("line", 100, 100), ("line", 0, 100)),
                       closed=False)
        self.assertEqual(plan_order((line, square(200)), (square(200), line)).order, (1, 0))
        self.assertIsNone(plan_order((square(0), square(200)), (square(200), line)).order)


class PlanContoursTests(unittest.TestCase):
    """Match contours to Default (Points tab): start points and directions per contour."""

    def test_rotates_a_contour_to_the_default_start_point(self):
        plan = plan_contours(Outline((square(200), D)), Outline((square(200), turn(D, 1))))
        self.assertEqual(plan.fixes, (ContourFix(1, reverse=False, start=5),))
        self.assertEqual(plan.refused, ())

    def test_reverses_a_contour_running_the_other_way(self):
        plan = plan_contours(Outline((D, square(200))),
                             Outline((D, square(200, reverse=True))))
        self.assertEqual(plan.fixes, (ContourFix(1, reverse=True, start=0),))

    def test_reverses_and_rotates_together(self):
        plan = plan_contours(Outline((D,)), Outline((turn(D_CLOCKWISE, 2),)))
        self.assertEqual(plan.fixes, (ContourFix(0, reverse=True, start=2),))

    def test_lists_contours_it_cannot_match(self):
        extra = Contour(D.points[:1] + (("line", 30, 0),) + D.points[1:])
        line = Contour(square(200).points, closed=False)
        plan = plan_contours(Outline((D, square(200))), Outline((extra, line)))
        self.assertEqual(plan.fixes, ())
        self.assertEqual(plan.refused, ((0, "points differ, see Contour order"),
                                        (1, "open, the Default source's contour is closed")))

    def test_a_start_point_point_types_cannot_tell_is_reported_not_changed(self):
        plan = plan_contours(Outline((STADIUM,)), Outline((turn(STADIUM, 3),)))
        self.assertEqual(plan.fixes, ())
        self.assertEqual(plan.refused, ((0, "can't tell from point types"),))

    def test_a_start_point_that_fits_the_point_types_is_left_alone(self):
        plan = plan_contours(Outline((STADIUM,)), Outline((turn(STADIUM, 4),)))
        self.assertEqual((plan.fixes, plan.refused), ((), ()))

    def test_direction_still_comes_from_the_winding_when_the_start_point_cannot(self):
        plan = plan_contours(Outline((STADIUM,)), Outline((STADIUM_CLOCKWISE,)))
        self.assertEqual(plan.fixes, (ContourFix(0, reverse=True, start=0),))
        self.assertEqual(plan.refused,
                         ((0, "reversed, but can't tell the start point from point types"),))

    def test_contours_pair_by_index_not_by_order(self):
        plan = plan_contours(Outline((D, square(200))), Outline((square(200), turn(D, 1))))
        self.assertEqual(plan.fixes, ())
        self.assertEqual(plan.refused, ((0, "points differ, see Contour order"),
                                        (1, "points differ, see Contour order")))

    def test_contours_without_a_default_partner(self):
        plan = plan_contours(Outline((D,)), Outline((D, square(200))))
        self.assertEqual(plan.refused, ((1, "no contour 2 in the Default source"),))

    def test_contours_only_in_the_default_source(self):
        plan = plan_contours(Outline((D, square(200), square(400))), Outline((D,)))
        self.assertEqual(plan.refused, ((1, "only in the Default source"),
                                        (2, "only in the Default source")))


class DescribeTests(unittest.TestCase):
    """What a Contour order cell says: direction and point count."""

    def test_counter_clockwise_and_clockwise(self):
        self.assertEqual(describe(square(10, 20)), ("counter-clockwise", 4))
        self.assertEqual(describe(D), ("counter-clockwise", 6))
        self.assertEqual(describe(square(reverse=True, start=2)), ("clockwise", 4))

    def test_open_contour(self):
        line = Contour((("move", 5, 0), ("line", 100, 0), ("line", 100, 50)), closed=False)
        self.assertEqual(describe(line), ("open", 3))


def draw(glyph, *contours):
    pen = glyph.getPointPen()
    for contour in contours:
        pen.beginPath()
        for kind, x, y in contour.points:
            pen.addPoint((x, y), None if kind == "offcurve" else kind)
        pen.endPath()


class LinkTests(unittest.TestCase):
    """Links join matching points of the current source and another source."""

    def wrong(self, found):
        return [(link.contour, link.point) for link in found.links if not link.good]

    def test_same_structure_links_every_point_and_is_compatible(self):
        found = links(Outline((square(), D)), Outline((square(size=140), D)))
        self.assertEqual(len(found.links), 10)
        self.assertEqual(self.wrong(found), [])
        self.assertIsNone(found.first_difference)
        self.assertEqual(found.status(), "compatible")

    def test_other_start_point_makes_every_link_of_that_contour_wrong(self):
        found = links(Outline((square(), D)), Outline((square(), turn(bolder(D), 1))))
        self.assertEqual(self.wrong(found), [(1, point) for point in range(6)])
        self.assertIsNone(found.first_difference)
        self.assertEqual(found.status(), "6 wrong links")

    def test_a_start_point_point_types_cannot_tell_apart_links_as_drawn(self):
        found = links(Outline((square(),)), Outline((square(size=140, start=1),)))
        self.assertEqual(self.wrong(found), [])

    def test_other_direction_keeps_only_the_start_point_link(self):
        found = links(Outline((square(),)), Outline((square(reverse=True),)))
        self.assertEqual(self.wrong(found), [(0, 1), (0, 3)])
        self.assertEqual(found.status(), "2 wrong links")

    def test_reversed_open_contour_makes_every_link_wrong(self):
        # A curve then a line: point types show which end comes first.
        stroke = Contour((("move", 0, 0), ("offcurve", 10, 50), ("curve", 50, 50),
                          ("line", 100, 0)), closed=False)
        backwards = Contour((("move", 100, 0), ("line", 50, 50), ("offcurve", 10, 50),
                             ("curve", 0, 0)), closed=False)
        found = links(Outline((stroke,)), Outline((backwards,)))
        self.assertEqual(self.wrong(found), [(0, 0), (0, 1), (0, 2), (0, 3)])

    def test_contours_in_another_order_make_every_link_of_the_moved_ones_wrong(self):
        current = Outline((square(), square(200), square(400)))
        other = Outline((square(), square(400), square(200)))
        found = links(current, other)
        self.assertEqual(self.wrong(found), [(c, p) for c in (1, 2) for p in range(4)])
        self.assertEqual(found.status(), "8 wrong links")

    def test_extra_point_marks_where_the_point_types_first_differ(self):
        # Line, line, then the extra line point where D has its first off-curve.
        extra = Contour(D.points[:1] + (("line", 30, 0),) + D.points[1:])
        found = links(Outline((square(), D)), Outline((square(), extra)))
        self.assertEqual(found.first_difference, (1, 2))
        self.assertEqual(self.wrong(found), [(1, 2), (1, 3), (1, 4), (1, 5)])
        self.assertEqual(found.status(), "4 wrong links · points differ in contour 2")

    def test_open_against_closed_differs_from_the_start_point(self):
        stroke = Contour((("move", 0, 0), ("line", 50, 10), ("line", 100, 0)), closed=False)
        triangle = Contour((("move", 0, 0), ("line", 50, 10), ("line", 100, 0)))
        found = links(Outline((stroke,)), Outline((triangle,)))
        self.assertEqual(found.first_difference, (0, 0))
        self.assertEqual(found.wrong, 3)

    def test_extra_contour_is_the_first_difference(self):
        found = links(Outline((square(), square(200))), Outline((square(), square(200), D)))
        self.assertEqual(self.wrong(found), [])
        self.assertEqual(found.first_difference, (2, 0))
        self.assertEqual(found.status(), "3 contours, current source has 2")

    def test_missing_contour_is_the_first_difference(self):
        found = links(Outline((square(), square(200), D)), Outline((square(), square(200))))
        self.assertEqual(found.first_difference, (2, 0))
        self.assertEqual(found.status(), "2 contours, current source has 3")

    def test_same_structure_contours_pair_by_position(self):
        # Two squares, listed the other way round in a bolder source.
        current = Outline((square(0), square(300)))
        other = Outline((square(310, size=140), square(-10, size=140)))
        self.assertEqual(self.wrong(links(current, other)),
                         [(c, p) for c in (0, 1) for p in range(4)])


class ContourIssueTests(unittest.TestCase):
    """The contours of a source that don't match the Default contour with the
    same index, tinted red in the Contour order tab."""

    def test_a_contour_with_another_start_point_has_an_issue(self):
        default = Outline((square(), D))
        self.assertEqual(contour_issues(default, Outline((square(), turn(bolder(D), 1)))), {1})

    def test_a_contour_without_a_partner_in_the_default_source_has_an_issue(self):
        self.assertEqual(contour_issues(Outline((square(),)), Outline((square(), D))), {1})

    def test_a_contour_with_an_extra_last_point_has_an_issue(self):
        longer = Contour(D.points + (("line", 0, 50),))
        self.assertEqual(contour_issues(Outline((square(), D)), Outline((square(), longer))), {1})

    def test_contours_in_another_order_both_have_an_issue(self):
        default = Outline((square(), square(200), D))
        self.assertEqual(contour_issues(default, Outline((square(200), square(), D))), {0, 1})

    def test_a_matching_glyph_has_no_issues(self):
        default = Outline((square(), D))
        self.assertEqual(contour_issues(default, Outline((square(size=140), bolder(D)))), set())


class SessionOutlineTests(unittest.TestCase):
    """Regular (default, with a 'medium' layer-source) + Bold, all closed."""

    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        root = Path(self._directory.name).resolve()
        regular, bold = root / "Regular.ufo", root / "Bold.ufo"
        font = Font()
        for name in ("A", "B", "C"):
            draw(font.newGlyph(name), D, square(200))
        font.newGlyph("E").getPointPen().addComponent("A", (1, 0, 0, 1, 0, 0))
        medium = font.newLayer("medium")
        draw(medium.newGlyph("A"), D, square(200))
        draw(medium.newGlyph("C"), turn(D, 1), square(200))   # start point
        font.save(str(regular))
        font = Font()
        draw(font.newGlyph("A"), D, square(200, size=130))
        draw(font.newGlyph("B"), square(200), D)              # contour order
        draw(font.newGlyph("C"), D, square(200, reverse=True))  # direction
        font.newGlyph("E")                                    # components
        font.save(str(bold))

        document = DesignSpaceDocument()
        axis = AxisDescriptor()
        axis.name, axis.tag = "Weight", "wght"
        axis.minimum, axis.default, axis.maximum = 0, 0, 1000
        document.addAxis(axis)
        for name, path, weight, layer in (("Regular", regular, 0, None),
                                          ("Medium", regular, 500, "medium"),
                                          ("Bold", bold, 1000, None)):
            source = SourceDescriptor()
            source.path, source.name, source.location = str(path), name, {"Weight": weight}
            source.layerName = layer
            document.addSource(source)
        designspace = root / "Test.designspace"
        document.write(designspace)
        self.session = CleanupSession(*load_designspace(designspace), open_fonts=dict)

    def tearDown(self):
        self._directory.cleanup()

    def test_scan_lists_glyphs_with_their_kinds_per_source(self):
        audit, _report = self.session.scan()
        rows = [(row.glyph, row.mismatches) for row in audit.outlines.rows]
        self.assertEqual(rows, [
            ("B", "Bold: contour order"),
            ("C", "Medium [medium]: start point · Bold: direction"),
            ("E", "Bold: components"),
        ])

    def test_audit_line_counts_kinds_and_sources(self):
        lines = [line.text for line in self.session.audit().lines()]
        self.assertIn("Outlines · contour order: 1 glyph (Bold 1) · start point: 1 glyph "
                      "(Medium [medium] 1) · direction: 1 glyph (Bold 1) · components: 1 glyph "
                      "(Bold 1)", lines)


class CurrentSourceTests(SessionOutlineTests):
    """What the Compatibility window reads for the current glyph."""

    def test_source_for_a_full_ufo_and_a_layer_source(self):
        regular = Path(self._directory.name).resolve() / "Regular.ufo"
        self.assertEqual(self.session.source_for(regular, None).label, "Regular")
        self.assertEqual(self.session.source_for(regular, "public.default").label, "Regular")
        self.assertEqual(self.session.source_for(regular, "medium").label, "Medium [medium]")

    def test_source_for_a_font_or_layer_outside_the_designspace(self):
        root = Path(self._directory.name).resolve()
        self.assertIsNone(self.session.source_for(root / "Other.ufo", None))
        self.assertIsNone(self.session.source_for(root / "Regular.ufo", "background"))

    def test_glyph_outlines_in_designspace_order_with_absent_as_none(self):
        found = [(source.label, outline) for source, outline in self.session.glyph_outlines("B")]
        self.assertEqual(found, [
            ("Regular", Outline((D, square(200)))),
            ("Medium [medium]", None),
            ("Bold", Outline((square(200), D))),
        ])


def saved_contours(path, name, layer=None):
    """The glyph's contours as written to disk."""
    font = Font(str(path))
    glyph = (font.layers[layer] if layer else font)[name]
    return tuple(Contour(tuple((point.segmentType or "offcurve", point.x, point.y)
                               for point in contour), not contour.open)
                 for contour in glyph)


class ContourOrderFixTests(SessionOutlineTests):
    """Reordering contours; every source here is a closed UFO."""

    def setUp(self):
        super().setUp()
        self.root = Path(self._directory.name).resolve()

    def test_reorder_one_source_saves_the_new_order(self):
        result = self.session.reorder_contours("Bold", "B", (1, 0))
        self.assertEqual(result.changed, ("Bold",))
        self.assertEqual(result.saved, ("Bold",))
        self.assertEqual(result.refused, ())
        self.assertEqual(saved_contours(self.root / "Bold.ufo", "B"), (D, square(200)))

    def test_reorder_refuses_an_order_that_is_not_one_of_the_contours(self):
        for order in ((0,), (0, 0), (0, 2), (1, 0, 2)):
            result = self.session.reorder_contours("Bold", "B", order)
            self.assertEqual((result.changed, result.saved), ((), ()))
            self.assertEqual(result.refused, (("Bold", "the new order doesn't list "
                                               "each of the 2 contours once"),))
        self.assertEqual(saved_contours(self.root / "Bold.ufo", "B"), (square(200), D))

    def test_reorder_refuses_a_glyph_the_source_lacks(self):
        result = self.session.reorder_contours("Medium [medium]", "B", (0,))
        self.assertEqual(result.refused, (("Medium [medium]", "no glyph B"),))

    def test_match_order_to_default_refuses_a_glyph_the_default_lacks(self):
        bold = Font(str(self.root / "Bold.ufo"))
        draw(bold.newGlyph("G"), D)
        bold.save()
        result = self.session.match_order_to_default("G")
        self.assertEqual((result.changed, result.saved), ((), ()))
        self.assertEqual(result.refused, (("Regular", "no glyph G"),))

    def test_match_order_to_default_fixes_only_sources_out_of_order(self):
        result = self.session.match_order_to_default("B")
        self.assertEqual((result.changed, result.saved, result.refused),
                         (("Bold",), ("Bold",), ()))
        self.assertEqual(saved_contours(self.root / "Bold.ufo", "B"), (D, square(200)))
        self.assertEqual(self.session.match_order_to_default("B").changed, ())
        outlines = [line.text for line in self.session.audit().lines()
                    if line.text.startswith("Outlines")]
        self.assertNotIn("contour order", outlines[0])

    def test_match_order_to_default_refuses_a_different_contour_count(self):
        regular = Font(str(self.root / "Regular.ufo"))
        draw(regular.newGlyph("F"), D, square(200))
        draw(regular.layers["medium"].newGlyph("F"), square(200))
        regular.save()
        bold = Font(str(self.root / "Bold.ufo"))
        draw(bold.newGlyph("F"), square(200), D)
        bold.save()
        result = self.session.match_order_to_default("F")
        self.assertEqual(result.changed, ("Bold",))
        self.assertEqual(result.saved, ("Bold",))
        self.assertEqual(result.refused,
                         (("Medium [medium]", "1 contour, the Default source has 2"),))
        self.assertEqual(saved_contours(self.root / "Regular.ufo", "F", "medium"),
                         (square(200),))
        self.assertEqual(saved_contours(self.root / "Bold.ufo", "F"), (D, square(200)))


class PointsFixTests(SessionOutlineTests):
    """Match contours to Default on the current source; every source here is a closed UFO."""

    def setUp(self):
        super().setUp()
        self.root = Path(self._directory.name).resolve()

    def test_match_default_fixes_direction_and_saves(self):
        result = self.session.match_contours_to_default("Bold", "C")
        self.assertEqual((result.changed, result.saved, result.refused, result.contours),
                         (("Bold",), ("Bold",), (), 1))
        self.assertEqual(saved_contours(self.root / "Bold.ufo", "C"), (D, square(200)))

    def test_match_default_fixes_a_start_point_in_a_layer_source(self):
        result = self.session.match_contours_to_default("Medium [medium]", "C")
        self.assertEqual((result.changed, result.saved), (("Medium [medium]",),) * 2)
        self.assertEqual(saved_contours(self.root / "Regular.ufo", "C", "medium"),
                         (D, square(200)))

    def test_match_default_reports_what_point_types_cannot_settle(self):
        bold = Font(str(self.root / "Bold.ufo"))
        draw(bold.newGlyph("S"), turn(STADIUM, 3), square(200))
        bold.save()
        regular = Font(str(self.root / "Regular.ufo"))
        draw(regular.newGlyph("S"), STADIUM)
        regular.save()
        result = self.session.match_contours_to_default("Bold", "S")
        self.assertEqual((result.changed, result.contours), ((), 0))
        self.assertEqual(result.refused, (
            ("Bold", "contour 1: can't tell from point types"),
            ("Bold", "contour 2: no contour 2 in the Default source")))
        self.assertEqual(saved_contours(self.root / "Bold.ufo", "S"),
                         (turn(STADIUM, 3), square(200)))

    def test_match_default_refuses_the_default_source_and_absent_glyphs(self):
        self.assertEqual(self.session.match_contours_to_default("Regular", "C").refused,
                         (("Regular", "this is the Default source"),))
        self.assertEqual(self.session.match_contours_to_default("Medium [medium]", "B").refused,
                         (("Medium [medium]", "no glyph B"),))

    def test_match_default_fixes_what_it_can_and_lists_the_rest(self):
        bold = Font(str(self.root / "Bold.ufo"))
        extra = Contour(D.points[:1] + (("line", 30, 0),) + D.points[1:])
        bold["C"].clearContours()
        draw(bold["C"], extra, square(200, reverse=True))
        bold.save()
        result = self.session.match_contours_to_default("Bold", "C")
        self.assertEqual((result.changed, result.saved), (("Bold",), ("Bold",)))
        self.assertEqual(result.refused,
                         (("Bold", "contour 1: points differ, see Contour order"),))
        self.assertEqual(saved_contours(self.root / "Bold.ufo", "C"), (extra, square(200)))


class OpenFontContourOrderTests(SessionOutlineTests):
    """Bold is open in RoboFont: changed in place with undo, never saved."""

    def setUp(self):
        super().setUp()
        from test_cleanup_fixes import _OpenFont
        root = Path(self._directory.name).resolve()
        self.bold = root / "Bold.ufo"
        self.open = _OpenFont(self.bold)
        fonts = {self.bold: self.open}
        self.session = CleanupSession(*load_designspace(root / "Test.designspace"),
                                      open_fonts=lambda: fonts)

    def test_match_order_to_default_uses_undo_and_leaves_the_font_unsaved(self):
        result = self.session.match_order_to_default("B")
        self.assertEqual((result.changed, result.saved), (("Bold",), ()))
        glyph = self.open.naked()["B"]
        self.assertEqual([len(contour) for contour in glyph], [6, 4])
        self.assertEqual(self.open.log, [("undo", "B", "Match Order to Default"),
                                         ("changed", "B")])
        self.assertEqual(saved_contours(self.bold, "B"), (square(200), D))

    def test_match_default_uses_undo_and_leaves_the_font_unsaved(self):
        result = self.session.match_contours_to_default("Bold", "C")
        self.assertEqual((result.changed, result.saved, result.contours), (("Bold",), (), 1))
        self.assertEqual(self.open.log, [("undo", "C", "Match Contours to Default"),
                                         ("changed", "C")])
        glyph = self.open.naked()["C"]
        self.assertEqual([(p.x, p.y) for p in glyph[1]],
                         [(200, 0), (300, 0), (300, 100), (200, 100)])
        self.assertEqual(saved_contours(self.bold, "C"), (D, square(200, reverse=True)))


class CompatibleSessionTests(unittest.TestCase):
    def test_compatible_line(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            document = DesignSpaceDocument()
            axis = AxisDescriptor()
            axis.name, axis.tag = "Weight", "wght"
            axis.minimum, axis.default, axis.maximum = 0, 0, 1000
            document.addAxis(axis)
            for name, weight in (("Regular", 0), ("Bold", 1000)):
                font = Font()
                draw(font.newGlyph("A"), D)
                font.save(str(root / f"{name}.ufo"))
                source = SourceDescriptor()
                source.path, source.name = str(root / f"{name}.ufo"), name
                source.location = {"Weight": weight}
                document.addSource(source)
            document.write(root / "Test.designspace")
            session = CleanupSession(*load_designspace(root / "Test.designspace"),
                                     open_fonts=dict)
            audit = session.audit()
            self.assertEqual(audit.outlines.rows, ())
            self.assertIn("Outlines · compatible", [line.text for line in audit.lines()])


if __name__ == "__main__":
    unittest.main()


class SameShapeContourOrderTests(unittest.TestCase):
    """Contours with the same point structure, in the order they should be (#13)."""

    def test_won_bars_at_one_height_are_in_order(self):
        # YTFI290 drops all four bars of "won" to one height; Fontra and
        # fontTools both find the glyph compatible.
        from amstelvar_glyphs import WON_DEFAULT, WON_YTFI290
        self.assertEqual(contour_issues(WON_DEFAULT, WON_YTFI290), frozenset())

    def test_a_counter_centred_in_its_outer_contour_is_in_order(self):
        from amstelvar_glyphs import O_DEFAULT, O_OPSZ8_WDTH50
        self.assertEqual(mismatches(O_DEFAULT, O_OPSZ8_WDTH50), set())

    def _won_with_bars_rotated(self):
        # Source contours 3-6 hold Default bars 6, 3, 4, 5: a real mistake.
        from amstelvar_glyphs import WON_YTFI290
        c = WON_YTFI290.contours
        return Outline((c[0], c[1], c[5], c[2], c[3], c[4]))

    def test_bars_out_of_order_are_reported(self):
        from amstelvar_glyphs import WON_DEFAULT
        rotated = self._won_with_bars_rotated()
        self.assertIn("contour order", mismatches(WON_DEFAULT, rotated))
        self.assertEqual(contour_issues(WON_DEFAULT, rotated), frozenset({2, 3, 4, 5}))

    def test_match_order_puts_rotated_bars_back(self):
        from amstelvar_glyphs import WON_DEFAULT
        self.assertEqual(plan_order(WON_DEFAULT.contours,
                                    self._won_with_bars_rotated().contours).order,
                         (0, 1, 3, 4, 5, 2))
