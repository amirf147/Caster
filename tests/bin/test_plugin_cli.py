"""
Unit tests for Caster plugin_cli tool.
"""

import argparse
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from castervoice.bin import plugin_cli
from castervoice.lib.ctrl.mgr import plugin_support


class TestPluginCLI(unittest.TestCase):

    def test_user_plugins_dir_resolution(self):
        """Verifies get_user_plugins_dir resolves a valid Path."""
        p = plugin_support.get_user_plugins_dir()
        self.assertIsInstance(p, Path)
        self.assertTrue(p.name == "plugins")

    def test_builtin_plugins_dir_resolution(self):
        """Verifies get_builtin_plugins_dir resolves the in-tree plugins directory."""
        p = plugin_support.get_builtin_plugins_dir()
        self.assertIsInstance(p, Path)
        self.assertTrue(p.name == "plugins")
        self.assertTrue(p.is_dir())

    def test_registry_fetch_failure_handling(self):
        """Verifies network failures return None gracefully without raising exceptions."""
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            result = plugin_support.fetch_registry("https://invalid.example.com/manifest.json")
            self.assertIsNone(result)

    def test_fetch_local_registry(self):
        """Verifies fetch_registry reads a local JSON file."""
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            json.dump({"plugins": {"test_plug": {"version": "1.0"}}}, f)
            temp_path = f.name
        try:
            reg = plugin_support.fetch_registry(temp_path)
            self.assertIsNotNone(reg)
            self.assertIn("test_plug", reg.get("plugins", {}))
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_set_plugin_enabled_preserves_table(self):
        """Verifies set_plugin_enabled updates boolean while preserving dictionary configuration."""
        import tomlkit
        doc = tomlkit.document()
        doc["plugins"] = tomlkit.table()
        doc["plugins"]["themed_hud"] = {"enabled": True, "port": 8080}
        doc["plugins"]["simple_plug"] = True

        with patch("castervoice.lib.ctrl.mgr.plugin_support.load_settings_toml", return_value=doc), \
             patch("castervoice.lib.ctrl.mgr.plugin_support.save_settings_toml") as mock_save:
            plugin_support.set_plugin_enabled("themed_hud", False)
            self.assertEqual(doc["plugins"]["themed_hud"]["enabled"], False)
            self.assertEqual(doc["plugins"]["themed_hud"]["port"], 8080)
            mock_save.assert_called_once()

    def test_cmd_enable_and_disable(self):
        """Verifies CLI enable and disable subcommands."""
        args = argparse.Namespace(name="test_plug")
        with patch("castervoice.bin.plugin_cli.set_plugin_enabled") as mock_set:
            plugin_cli.cmd_enable(args)
            mock_set.assert_called_with("test_plug", True)

            plugin_cli.cmd_disable(args)
            mock_set.assert_called_with("test_plug", False)

    def test_cmd_info(self):
        """Verifies CLI info subcommand outputs metadata."""
        args = argparse.Namespace(name="themed_hud", registry="test_reg")
        registry_data = {
            "plugins": {
                "themed_hud": {
                    "version": "1.0.0",
                    "author": "tester",
                    "description": "Custom HUD",
                    "platforms": ["windows", "linux"],
                }
            }
        }
        with patch("castervoice.bin.plugin_cli.load_settings_toml", return_value={"plugins": {"themed_hud": True}}), \
             patch("castervoice.bin.plugin_cli.fetch_registry", return_value=registry_data), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            plugin_cli.cmd_info(args)
            out = mock_stdout.getvalue()
            self.assertIn("themed_hud", out)
            self.assertIn("1.0.0", out)
            self.assertIn("tester", out)


if __name__ == "__main__":
    unittest.main()
