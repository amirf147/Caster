# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Amir Farhadi

"""
Unit tests for Caster plugin_cli tool.
"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from castervoice.bin import plugin_cli


class TestPluginCLI(unittest.TestCase):

    def test_user_plugins_dir_resolution(self):
        """Verifies get_user_plugins_dir resolves a valid Path."""
        p = plugin_cli.get_user_plugins_dir()
        self.assertIsInstance(p, Path)
        self.assertTrue(p.name == "plugins")

    def test_builtin_plugins_dir_resolution(self):
        """Verifies get_builtin_plugins_dir resolves the in-tree plugins directory."""
        p = plugin_cli.get_builtin_plugins_dir()
        self.assertIsInstance(p, Path)
        self.assertTrue(p.name == "plugins")
        self.assertTrue(p.is_dir())

    def test_registry_fetch_failure_handling(self):
        """Verifies network failures return None gracefully without raising exceptions."""
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            result = plugin_cli.fetch_registry("https://invalid.example.com/manifest.json")
            self.assertIsNone(result)

    def test_fetch_local_registry(self):
        """Verifies fetch_registry reads a local JSON file."""
        import tempfile, json
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump({"plugins": {"test_plug": {"version": "1.0"}}}, f)
            temp_path = f.name
        try:
            reg = plugin_cli.fetch_registry(temp_path)
            self.assertIsNotNone(reg)
            self.assertIn("test_plug", reg.get("plugins", {}))
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
