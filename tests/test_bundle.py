from __future__ import annotations

import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "TDBKRFTools.roboFontExt"
PACKAGE = BUNDLE / "lib" / "tdbk_rftools"


class BundleTests(unittest.TestCase):

    def test_bundle_metadata_and_menu_path(self):
        with (BUNDLE / "info.plist").open("rb") as stream:
            info = plistlib.load(stream)
        self.assertEqual(info["name"], "TDBK RFTools")
        self.assertEqual(info["version"], "1.0.0")
        self.assertEqual(info["requiresVersionMajor"], "4")
        self.assertEqual(info["requiresVersionMinor"], "6")
        self.assertEqual(
            info["addToMenu"],
            [{"path": "startup.py", "preferredName": "TDBK RFTools", "shortKey": ""}],
        )
        self.assertTrue(info["launchAtStartUp"])
        self.assertEqual(info["mainScript"], "start.py")

    def test_tests_are_outside_the_bundle(self):
        self.assertTrue((BUNDLE / "lib" / "startup.py").is_file())
        self.assertFalse((BUNDLE / "tests").exists())

    def test_palette_holds_exactly_the_public_tools(self):
        palette = (PACKAGE / "palette.py").read_text()
        tools_init = (PACKAGE / "tools" / "__init__.py").read_text()
        for name in ("SelectedPointsTool", "ContourProbeTool",
                     "DistributePointsTool", "CleanupTool"):
            self.assertIn(name, tools_init)
            self.assertNotIn(name, palette)
        tools = sorted(path.stem for path in (PACKAGE / "tools").glob("*.py"))
        self.assertEqual(tools, [
            "__init__", "base", "cleanup", "contour_probe", "contour_probe_model",
            "contour_probe_state", "distribute_points", "distribute_points_model",
            "selected_points", "selected_points_model", "selected_points_state",
        ])

    def test_every_tool_wires_its_own_callbacks(self):
        for name in ("selected_points", "contour_probe", "distribute_points", "cleanup"):
            source = (PACKAGE / "tools" / f"{name}.py").read_text()
            self.assertIn("(PaletteTool):", source, name)
            # Callbacks are the tool's own functions, never controller method names.
            self.assertNotIn('"callback": "', source, name)

    def test_one_shot_actions_never_subscribe(self):
        source = (PACKAGE / "tools" / "distribute_points.py").read_text()
        self.assertIn("glyph.undo(", source)
        self.assertNotIn("registerGlyphEditorSubscriber", source)


if __name__ == "__main__":
    unittest.main()
