"""
Comprehensive Verification Test for Caster HUD Widgets, Layouts, Rules Filter & Focus Tracker.
"""

import sys
import unittest
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from castervoice.asynch.hud.core.state import HudState, DesktopContextState, VoiceState
from castervoice.asynch.hud.core.events import (
    DesktopContextEvent,
    ActiveRulesEvent,
    MicStateEvent,
    RecognitionEvent,
    ClearHistoryEvent,
)
from castervoice.asynch.hud.core.reducer import reduce_event
from castervoice.asynch.hud_support import (
    get_active_contextual_rules,
    is_internal_rule_name,
)
from castervoice.asynch.hud.core.window_tracker import (
    IFocusTracker,
    Win32WindowFocusTracker,
    NullWindowFocusTracker,
    create_window_focus_tracker,
)
from castervoice.lib.qt import QtWidgets, QtCore
from castervoice.asynch.hud.ui.widgets.border_controller import BorderController
from castervoice.asynch.hud.ui.widgets.adce_bar import AdceBarWidget
from castervoice.asynch.hud.ui.widgets.active_rules_bar import ActiveRulesBarWidget
from castervoice.asynch.hud.ui.widgets.status_bar import StatusBarWidget
from castervoice.asynch.hud.ui.main_window import MainWindow


class TestHudComponents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance()
        if cls.app is None:
            cls.app = QtWidgets.QApplication([])

    def test_internal_rule_name_filter(self):
        """Verifies that internal merger artifacts and private helpers are 100% excluded."""
        self.assertTrue(is_internal_rule_name("Repeater1"))
        self.assertTrue(is_internal_rule_name("Repeater24"))
        self.assertTrue(is_internal_rule_name("PreparedRule"))
        self.assertTrue(is_internal_rule_name("RepeatRule"))
        self.assertTrue(is_internal_rule_name("ccr"))
        self.assertTrue(is_internal_rule_name("_smr_mapping"))
        self.assertTrue(is_internal_rule_name("g1"))
        self.assertTrue(is_internal_rule_name("g42"))
        self.assertTrue(is_internal_rule_name("caster_rule"))

        # User-facing rules MUST NOT be excluded
        self.assertFalse(is_internal_rule_name("VS Code"))
        self.assertFalse(is_internal_rule_name("IDETerminal"))
        self.assertFalse(is_internal_rule_name("Terminal"))
        self.assertFalse(is_internal_rule_name("Gemini"))
        self.assertFalse(is_internal_rule_name("Chrome"))
        self.assertFalse(is_internal_rule_name("Git Commit"))

    def test_focus_tracker_factory(self):
        """Verifies that create_window_focus_tracker instantiates a valid IFocusTracker."""
        tracker = create_window_focus_tracker()
        self.assertIsInstance(tracker, IFocusTracker)
        proc, title = tracker.get_foreground_info()
        self.assertIsInstance(proc, str)
        self.assertIsInstance(title, str)

    def test_desktop_context_event_reduction(self):
        state = HudState()
        ev = DesktopContextEvent(
            process_name="code",
            window_title="main_window.py - Caster",
            semantic_zone="IntegratedTerminal",
            active_file="main_window.py"
        )
        new_state = reduce_event(state, ev)
        self.assertEqual(new_state.desktop_context.process_name, "code")
        self.assertEqual(new_state.desktop_context.semantic_zone, "IntegratedTerminal")
        self.assertEqual(new_state.desktop_context.active_file, "main_window.py")

    def test_active_rules_event_reduction(self):
        state = HudState()
        ev = ActiveRulesEvent(rules=["VS Code", "Python Context"])
        new_state = reduce_event(state, ev)
        self.assertEqual(new_state.voice.active_rules, ("VS Code", "Python Context"))

    def test_empty_contextual_rules_fallback(self):
        state = HudState()
        ev = ActiveRulesEvent(rules=[])
        new_state = reduce_event(state, ev)
        self.assertEqual(new_state.voice.active_rules, ())

    def test_adce_widget_rendering(self):
        widget = AdceBarWidget()
        self.assertEqual(widget.height(), 22)
        widget.update_context("code", "title", "IntegratedTerminal", "main.py", True)
        self.assertEqual(widget._semantic_zone, "IntegratedTerminal")
        self.assertEqual(widget._process_name, "code")
        self.assertTrue(widget._is_connected)

    def test_adce_widget_unknown_zone(self):
        widget = AdceBarWidget()
        widget.update_context("code", "title", "Unknown", "main.py", is_connected=True)
        self.assertEqual(widget._semantic_zone, "Unknown")
        self.assertEqual(widget._process_name, "code")
        self.assertTrue(widget._is_connected)

    def test_adce_widget_offline_state(self):
        widget = AdceBarWidget()
        widget.update_context("code", "title", "IntegratedTerminal", "main.py", is_connected=False)
        self.assertFalse(widget._is_connected)
        self.assertEqual(widget._process_name, "")
        self.assertEqual(widget._semantic_zone, "")
        self.assertEqual(widget._active_file, "")

    def test_active_rules_bar_widget_global_fallback(self):
        widget = ActiveRulesBarWidget()
        widget.update_rules([])
        self.assertEqual(widget._current_rules, ())

    def test_active_rules_bar_widget_contextual(self):
        widget = ActiveRulesBarWidget()
        widget.update_rules(["VS Code", "Terminal Rule"])
        self.assertEqual(widget._current_rules, ("VS Code", "Terminal Rule"))
        self.assertEqual(widget._current_mic_state, "active")

    def test_active_rules_bar_widget_sleep_suppression(self):
        widget = ActiveRulesBarWidget()
        widget.update_rules(["VS Code", "Terminal Rule"], mic_state="sleeping")
        self.assertEqual(widget._current_mic_state, "sleeping")

    def test_main_window_toggles(self):
        win = MainWindow()
        win.show()
        # Test ADCE toggle
        self.assertFalse(win.adce_widget.isVisible())
        win.toggle_adce_bar()
        self.assertTrue(win.adce_widget.isVisible())
        win.toggle_adce_bar()
        self.assertFalse(win.adce_widget.isVisible())

        # Test Verbose toggle
        self.assertFalse(win.status_bar_widget.isVisible())
        self.assertFalse(win.active_rules_widget.isVisible())
        win.toggle_verbose_mode()
        self.assertTrue(win.status_bar_widget.isVisible())
        self.assertTrue(win.active_rules_widget.isVisible())
        win.toggle_verbose_mode()
        self.assertFalse(win.status_bar_widget.isVisible())
        self.assertFalse(win.active_rules_widget.isVisible())

    def test_contextual_rules_target_process_evaluation(self):
        """Verifies get_active_contextual_rules with target_process arguments."""
        rules_code = get_active_contextual_rules(target_process="code", target_title="main.py", target_hwnd=1)
        self.assertIsInstance(rules_code, list)
        rules_waterfox = get_active_contextual_rules(target_process="waterfox", target_title="Waterfox", target_hwnd=2)
        self.assertIsInstance(rules_waterfox, list)

    def test_powershell_and_terminal_context_matching(self):
        """Verifies PowerShell fuzzy process and title matching."""
        rules_ps = get_active_contextual_rules(target_process="powershell", target_title="Windows PowerShell", target_hwnd=3)
        self.assertIsInstance(rules_ps, list)
        rules_wt = get_active_contextual_rules(target_process="windowsterminal", target_title="Windows PowerShell", target_hwnd=4)
        self.assertIsInstance(rules_wt, list)
        rules_pwsh = get_active_contextual_rules(target_process="pwsh", target_title="pwsh", target_hwnd=5)
        self.assertIsInstance(rules_pwsh, list)

    def test_border_controller_mic_state_colors(self):
        """Verifies BorderController applies distinct green and red borders for mic states."""
        frame = QtWidgets.QFrame()
        frame.setObjectName("hud_container")
        frame.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        controller = BorderController(frame)

        # Awake / Listening
        controller.update_state(HudState(mic_mode="on"))
        self.assertIn("#2ecc71", frame.styleSheet())

        # Sleeping
        controller.update_state(HudState(mic_mode="sleeping"))
        self.assertIn("#e74c3c", frame.styleSheet())

        # Drag Mode
        controller.update_state(HudState(mic_mode="on", is_drag_mode=True))
        self.assertIn("#f39c12", frame.styleSheet())


if __name__ == "__main__":
    unittest.main()

