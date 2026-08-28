"""
Unit tests for Caster HUD UI Window, Dialogs, and Signal Bridge.
"""

import sys
import time
import unittest
from castervoice.lib.qt import QtWidgets, QtCore
from castervoice.asynch.hud.ui.main_window import MainWindow
from castervoice.asynch.hud.core.events import MicStateEvent, RecognitionEvent, DragModeEvent


class TestHudUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance()
        if cls.app is None:
            cls.app = QtWidgets.QApplication(sys.argv)

    def test_main_window_lifecycle_and_dialogs(self):
        window = MainWindow()
        window.show()
        self.app.processEvents()

        # Test Drag Mode toggle
        window.toggle_drag_mode()
        self.app.processEvents()
        self.assertTrue(window.state.is_drag_mode)
        self.assertEqual(window.state.get_border_color(), "#f39c12")  # Amber

        # Test Mic State Sleeping while Drag Mode (Mic takes priority)
        window.dispatch_event(MicStateEvent(mode="sleeping"))
        self.app.processEvents()
        self.assertEqual(window.state.get_border_color(), "#e74c3c")  # Red

        # Test Exit Drag Mode
        window.toggle_drag_mode()
        self.app.processEvents()
        self.assertFalse(window.state.is_drag_mode)

        # Test Show Help Dialog
        window.show_help_dialog()
        self.app.processEvents()
        self.assertIsNotNone(window.help_dialog)
        self.assertTrue(window.help_dialog.isVisible())
        window.hide_help_dialog()
        self.app.processEvents()
        self.assertFalse(window.help_dialog.isVisible())

        # Test Show Rules Dialog
        sample_rules_json = '[{"name": "TestGrammar", "rules": [{"name": "TestRule", "specs": ["spec1::action1"]}]}]'
        window.show_rules_dialog(sample_rules_json)
        self.app.processEvents()
        self.assertIsNotNone(window.rules_dialog)
        self.assertTrue(window.rules_dialog.isVisible())
        window.hide_rules_dialog()
        self.app.processEvents()
        self.assertIsNone(window.rules_dialog)

        # Test Show Profile Dialog
        window.show_profile_dialog("save")
        self.app.processEvents()
        self.assertIsNotNone(window.profile_dialog)
        self.assertTrue(window.profile_dialog.isVisible())
        window.profile_dialog.close()
        self.app.processEvents()

        window.close()
        self.app.processEvents()

    def test_caster_rule_grammar_import(self):
        """Verify that caster_rule.py imports cleanly and builds rule details without NameError."""
        import castervoice.rules.core.utility_rules.caster_rule as cr
        rule_class, details = cr.get_rule()
        self.assertIsNotNone(rule_class)
        self.assertIn("show caster hud", rule_class.mapping)
        self.assertIn("show caster rules", rule_class.mapping)
        self.assertIn("show caster [hud] help", rule_class.mapping)
        self.assertIn("caster hud (status | header | verbose) [toggle]", rule_class.mapping)
        self.assertIn("caster hud (rules strip | active rules) [toggle]", rule_class.mapping)


if __name__ == "__main__":
    unittest.main()
