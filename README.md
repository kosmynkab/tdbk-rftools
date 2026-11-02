# TDBK RFTools

A small RoboFont palette of drawing and checking tools:

- **Measure Selected Points**: distance, Δx, Δy and angle between two selected points.
- **Contour Probe**: live stem and counter widths under the cursor.
- **Distribute Points**: even spacing for three or more points or anchors.
- **Cleanup**: designspace-wide anchor, layer, guide and mark-colour fixes, an
  outline compatibility audit, and a Compatibility window for fixing
  mismatches glyph by glyph.

## Supported environment

- RoboFont 4.6;
- RoboFont's bundled Python 3.12;
- macOS.

No compatibility claim is made for earlier RoboFont releases.

## Installation

Download or clone this repository, double-click `TDBKRFTools.roboFontExt` and accept
RoboFont's installation prompt. Restart RoboFont or reload extensions. No
build step or third-party packages are needed: the extension uses RoboFont's
bundled EZUI, Subscriber and FontParts APIs.

## Menu

TDBK RFTools adds a top-level **TDBK RFTools** menu beside the other application menus.
**Open Palette** opens the palette, **Cleanup…** opens the designspace Cleanup
window (also available from the palette) and **Compatibility…** opens the
Compatibility window. **Extensions → TDBK RFTools** also opens the palette.

## Using the palette

### Measure Selected Points

Enable **Measure Selected Points**, then select exactly two contour points in
the active Glyph Editor. A live editor overlay displays:

- direct distance;
- horizontal and vertical distance (`Δx`, `Δy`);
- angle.

Measurements follow outline order: from the first selected point to the
second as they appear in the glyph's contours, so `Δx`, `Δy` and the angle
(−180° to 180°) carry a sign.

On-curve and off-curve contour points are supported. Other selected objects are
ignored. The overlay hides unless exactly two points are selected.

The tool is completely read-only. It does not change outlines, add data or
guidelines, dirty the glyph, or save the font.

### Contour Probe

Enable **Contour Probe** and move the cursor over a closed native contour. A
live perpendicular probe reports the local filled and unfilled intervals. It
follows curves using a cached adaptive flattening of cubic segments and is
recalculated only when the outline changes. It hides whenever a measurement
would be uncertain. Open contours and glyphs containing components are
deliberately unsupported in this first version, so they never produce a
potentially misleading result.

### Distribute Points

Select three or more on-curve points and/or anchors, then click **Horizontal**
or **Vertical** in the palette's **Distribute** row.

The participants are ranked by the coordinate on the chosen axis. The lowest
and highest keep their exact positions; everything in between is respaced so
the gaps are equal. The other axis is never touched, so a horizontal distribute
changes only `x` values.

- On-curve points and anchors participate as equals.
- Off-curve points are never participants. Instead, the handles attached to a
  moved on-curve point shift with it, so the curve around the node keeps its
  shape. A quadratic off-curve sitting between two moving on-curve points is
  left alone rather than guessed at.
- New coordinates are rounded to integers, so individual gaps may differ by one
  unit across an indivisible span. The outline stays on the integer grid.
- Points sharing a coordinate keep their relative order, so the same selection
  always produces the same result.
- Each click writes one undo record.

Unlike the measurement tools, this one has no on/off switch — it does nothing
until a button is clicked. If fewer than three points are selected, no glyph is
open, or the selection has no span along the chosen axis, nothing happens: the
glyph is untouched and no undo record is created. The reason is printed to the
Output window while `DEBUG` is on.

### Cleanup (designspace)

Click **Cleanup…** in the palette (or choose **TDBK RFTools → Cleanup…**),
then **Load Designspace…**. The designspace default is used; **Choose
Default…** picks another full source. The source list shows which sources are
open in RoboFont and which are closed. Layer-sources (`<source layer="…">`)
are included; one whose layer is missing is skipped with a warning.

**Audit.** After loading, and after every rescan or fix, the audit lists what
needs doing: glyph counts per anchor issue (missing, extra, order only,
duplicate names) with the sources involved, extra layers per UFO (background
layers on their own line), glyph and font guides, and glyphs with a mark colour.
Click an anchor line to select those glyphs in the Anchors list. The audit is
also the preview for the layer, guide and colour buttons below.

**Anchors.** Every glyph in the default whose anchors differ in another source
is listed: missing or extra anchor names, a different order, or duplicate
names. Glyphs absent from a source are allowed in a variable font and are only
counted. Select rows (Cmd-A for all), then:

- **Match Default** gives each source the default's anchor names in the
  default's order. Existing anchors keep their positions; missing ones are
  added at the default's coordinates and listed afterwards so you can check
  them. Rows with duplicate names are skipped.
- **Remove All Anchors** removes the glyph's anchors from every source,
  including the default.

**Layers · Guides · Mark colours.** Each button acts on the whole designspace
with no selection:

- **Remove Extra Layers** deletes every layer except each UFO's main layer and
  layers the designspace uses as sources. Background layers are removed too.
- **Remove Guides** deletes glyph guides in every source and font guides in
  each full UFO.
- **Strip Mark Colours** clears the mark colour of every glyph in every source.

Deleting layers and font guides in an open font has no undo; the report names
those fonts (revert the font to get them back).

**Absent glyphs.** The dropdown lists each source that lacks some of the
default's glyphs. The names below it are space-separated, ready to paste into
**Font → Add Glyphs**; **Copy** puts them on the clipboard.

**Outlines and Compatibility.** The Outlines tab lists glyphs whose contours
or components differ from the default source in a way that stops interpolation:
contour count, contour order, start point, direction, or point count and types.
Open a glyph from the list in the Compatibility window, which follows the
current Glyph Editor. Its **Points** tab draws the current source beside a
comparison source and links matching points; **Match Default** there gives
each contour the default's start point and direction. Its **Contour order** tab
shows every source's contours in order; **Match order to Default** reorders
them in every source. Compatibility is judged by point structure, never by
position alone.

Open fonts are changed with undo and left unsaved; closed UFOs are saved
immediately. The window rescans after each fix; **Rescan** refreshes it after
manual edits.

## Project structure

```text
TDBKRFTools.roboFontExt/
    info.plist                 extension metadata and menu entry
    lib/
        start.py               startup script (installs the menu)
        startup.py             Extensions-menu entry point
        tdbk_rftools/
            extension.py       singleton palette lifecycle
            menu.py            top-level menu
            palette.py         stacks the registered tools in one EZWindow
            geometry.py        the measuring rule and number formatting
            tools/             one module per palette tool, with pure *_model.py logic
            cleanup/           Cleanup and Compatibility windows and their pure logic
tests/
    check.sh                   the one development check
    offscreen/                 drivers that build the real windows offscreen
```

To add a tool, subclass `PaletteTool` in `tdbk_rftools/tools/`: give it an EZUI
`content` row and a `descriptions()` method whose callbacks are the tool's own
methods, then return the class from `get_tool_classes()`. The palette needs no
changes. Keep geometry and formatting independent of RoboFont. A tool that
subscribes to events must expose idempotent `start()` and `stop()` methods and
release its subscriber references in `stop()`.

## Development checks

```bash
sh tests/check.sh
```

It runs lint (`ruff`), checks that the pure modules import nothing from
RoboFont or AppKit, runs the unit tests and builds the windows offscreen, all
under RoboFont's bundled Python. It needs RoboFont in `/Applications` and
`ruff` (`brew install ruff`). Selection, editor switching and appearance still
need checking inside RoboFont.

## Thanks

Contour Probe is inspired by Rafał Buchner's
[StemThickness](https://github.com/RafalBuchner/StemThickness) plugin for
Glyphs.

The outline fixtures in `tests/amstelvar_glyphs.py` are a few glyphs from
[Amstelvar A2](https://github.com/googlefonts/amstelvar-avar2), licensed under
the SIL Open Font License 1.1.

## License

MIT. See [LICENSE](LICENSE).
