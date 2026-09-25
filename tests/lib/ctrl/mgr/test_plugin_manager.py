# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Amir Farhadi

"""
Unit tests for Caster PluginManager and PluginBase lifecycle contract.
"""

import unittest
from unittest.mock import MagicMock

from castervoice.lib.plugin import PluginBase
from castervoice.lib.ctrl.mgr.plugin_manager import PluginManager


class DummyPlugin(PluginBase):
    name = "dummy"

    def __init__(self):
        super(DummyPlugin, self).__init__()
        self.init_called = False
        self.start_called = False
        self.stop_called = False

    def initialize(self, nexus, config):
        super(DummyPlugin, self).initialize(nexus, config)
        self.init_called = True

    def start(self):
        super(DummyPlugin, self).start()
        self.start_called = True

    def stop(self):
        super(DummyPlugin, self).stop()
        self.stop_called = True


class TestPluginManager(unittest.TestCase):

    def setUp(self):
        self.mock_nexus = MagicMock()
        self.settings = {
            "plugins": {
                "dummy": True,
                "disabled_dummy": False,
                "standard_hud": True,
            }
        }
        self.manager = PluginManager(nexus=self.mock_nexus, settings_dict=self.settings)

    def test_plugin_base_lifecycle(self):
        """Verifies PluginBase lifecycle state transitions."""
        p = DummyPlugin()
        self.assertFalse(p.is_running)

        p.initialize(self.mock_nexus, {"test_key": "test_val"})
        self.assertTrue(p.init_called)
        self.assertEqual(p._config.get("test_key"), "test_val")

        p.start()
        self.assertTrue(p.start_called)
        self.assertTrue(p.is_running)

        p.stop()
        self.assertTrue(p.stop_called)
        self.assertFalse(p.is_running)

    def test_load_plugins_from_directory(self):
        """Verifies PluginManager discovers and instantiates enabled plugins from a directory."""
        import tempfile, shutil
        from pathlib import Path
        temp_dir = tempfile.mkdtemp()
        try:
            plug_dir = Path(temp_dir) / "test_plugin"
            plug_dir.mkdir()
            with open(plug_dir / "__init__.py", "w", encoding="utf-8") as f:
                f.write(
                    "from castervoice.lib.plugin import PluginBase\n"
                    "class TestPlug(PluginBase):\n"
                    "    name = 'test_plugin'\n"
                    "def get_plugin():\n"
                    "    return TestPlug()\n"
                )
            mgr = PluginManager(nexus=self.mock_nexus, settings_dict={"plugins": {"test_plugin": True}})
            mgr.load_plugins(plugin_dirs=[temp_dir])
            self.assertIsNotNone(mgr.get_plugin("test_plugin"))
            self.assertEqual(mgr.get_plugin("test_plugin").name, "test_plugin")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_plugin_start_and_stop(self):
        """Verifies PluginManager starts and stops loaded plugins."""
        dummy = DummyPlugin()
        self.manager._plugins["dummy"] = dummy

        self.manager.start_plugins()
        self.assertTrue(dummy.start_called)
        self.assertTrue(dummy.is_running)

        self.manager.stop_plugins()
        self.assertTrue(dummy.stop_called)
        self.assertFalse(dummy.is_running)

    def test_broken_plugin_handling(self):
        """Verifies that an error loading one plugin does not crash the manager."""
        # Attempt to load a non-existent plugin file directly
        self.manager._load_plugin_file("broken", "C:/path/does/not/exist/plugin.py", {})
        self.assertIsNone(self.manager.get_plugin("broken"))

    def test_plugin_rules_registration(self):
        """Verifies companion rules returned by get_rules() are registered with GrammarManager."""
        class DummyVoiceRule:
            pass

        class RuleProvidingPlugin(PluginBase):
            name = "rule_provider"
            def get_rules(self):
                return [DummyVoiceRule]

        self.manager._nexus._grammar_manager = MagicMock()
        provider = RuleProvidingPlugin()
        provider.initialize(self.manager._nexus, {})
        for r in provider.get_rules():
            self.manager._nexus._grammar_manager.add_rule(r)
        self.manager._nexus._grammar_manager.add_rule.assert_called_once_with(DummyVoiceRule)

    def test_dynamic_load_and_unload_plugin(self):
        """Verifies PluginManager dynamically loads, starts, stops, and unloads plugins."""
        dummy = DummyPlugin()
        self.manager._plugins["dummy"] = dummy
        dummy.start()
        self.assertTrue(dummy.is_running)

        success, msg = self.manager.unload_plugin("dummy")
        self.assertTrue(success)
        self.assertTrue(dummy.stop_called)
        self.assertFalse(dummy.is_running)
        self.assertIsNone(self.manager.get_plugin("dummy"))

    def test_replaces_hud_plugin_load_stops_current_hud(self):
        """Verifies loading a HUD replacement plugin stops the running HUD first."""
        from unittest.mock import patch
        class HudPlugin(PluginBase):
            name = "custom_hud"
            replaces_hud = True

        plugin = HudPlugin()
        self.manager._plugins["custom_hud"] = plugin
        with patch("castervoice.asynch.hud_support.stop_hud") as mock_stop:
            with patch.object(self.manager, "_default_plugin_directories", return_value=["/fake/dir"]):
                # Trigger dynamic load flow
                with patch.object(self.manager, "_load_plugin_file"):
                    with patch("os.path.isfile", return_value=True):
                        with patch("os.path.isdir", return_value=True):
                            success, msg = self.manager.load_plugin("custom_hud")
                            self.assertTrue(success)
                            mock_stop.assert_called_once()
                            self.assertTrue(plugin.is_running)

    def test_replaces_hud_plugin_unload_does_not_auto_restore_standard_hud(self):
        """Verifies unloading a HUD replacement plugin does not automatically pop up standard HUD."""
        from unittest.mock import patch
        class HudPlugin(PluginBase):
            name = "custom_hud"
            replaces_hud = True

        plugin = HudPlugin()
        self.manager._plugins["custom_hud"] = plugin
        plugin.start()
        self.manager._settings = {"hud": {"enabled": True}}

        with patch("castervoice.asynch.hud_support.start_hud") as mock_start:
            success, msg = self.manager.unload_plugin("custom_hud")
            self.assertTrue(success)
            mock_start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
