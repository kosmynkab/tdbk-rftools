from __future__ import annotations

import unittest

from tdbk_rftools.tools.base import PaletteTool


class PaletteToolTests(unittest.TestCase):
    def test_defaults_let_a_tool_override_only_what_it_needs(self):
        tool = PaletteTool()
        self.assertEqual(tool.descriptions(), {})
        window = object()
        tool.attach(window)
        self.assertIs(tool.window, window)
        tool.start()
        tool.refresh()
        tool.stop()


if __name__ == "__main__":
    unittest.main()
