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
                "adce": True,
                "taskbar_hud": True,
                "themed_hud": True,
                "standard_hud": False,
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

    def test_load_builtin_plugins(self):
        """Verifies PluginManager discovers and instantiates enabled built-in plugins."""
        self.manager.load_plugins()

        # Enabled plugins should be loaded
        self.assertIsNotNone(self.manager.get_plugin("adce"))
        self.assertIsNotNone(self.manager.get_plugin("taskbar_hud"))
        self.assertIsNotNone(self.manager.get_plugin("themed_hud"))

        # Disabled plugins should not be loaded
        self.assertIsNone(self.manager.get_plugin("standard_hud"))
        self.assertIsNone(self.manager.get_plugin("sikuli"))

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


if __name__ == "__main__":
    unittest.main()
