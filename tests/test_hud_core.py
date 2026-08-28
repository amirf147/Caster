"""
Unit tests for Caster HUD Core Domain (State, Events, Reducers, Constants).
"""

import unittest
from castervoice.asynch.hud.core import constants
from castervoice.asynch.hud.core.state import HudState, LogEntry, VoiceState, DesktopContextState
from castervoice.asynch.hud.core.events import (
    MicStateEvent,
    RecognitionEvent,
    ActiveRulesEvent,
    DesktopContextEvent,
    WindowFocusEvent,
    DragModeEvent,
    ThemeChangeEvent,
    ClearHistoryEvent,
    HeartbeatEvent,
    event_from_dict,
)
from castervoice.asynch.hud.core.reducer import reduce_event


class TestHudCore(unittest.TestCase):

    def test_default_state(self):
        state = HudState()
        self.assertEqual(state.mic_mode, "on")
        self.assertEqual(state.get_status_text(), "LISTENING")
        self.assertEqual(state.get_border_color(), constants.COLOR_MIC_ON)
        self.assertEqual(len(state.history), 0)

    def test_safety_border_priority_hierarchy(self):
        """
        Verify that Mic State (Red/Green) strictly takes priority over Focus (Blue)
        and Drag Mode (Amber).
        """
        # 1. Sleeping state (Must be Red, even if window is focused)
        state_sleeping_focused = HudState(mic_mode="sleeping", is_focused=True, is_drag_mode=False)
        self.assertEqual(state_sleeping_focused.get_border_color(), constants.COLOR_MIC_SLEEPING)

        # 2. Drag Mode active while mic on (Amber)
        state_drag = HudState(mic_mode="on", is_focused=True, is_drag_mode=True)
        self.assertEqual(state_drag.get_border_color(), constants.COLOR_DRAG)

        # 3. Focused while mic on (Blue)
        state_focused = HudState(mic_mode="on", is_focused=True, is_drag_mode=False)
        self.assertEqual(state_focused.get_border_color(), constants.COLOR_FOCUS)

        # 4. Normal listening unfocused (Green)
        state_listening = HudState(mic_mode="on", is_focused=False, is_drag_mode=False)
        self.assertEqual(state_listening.get_border_color(), constants.COLOR_MIC_ON)

    def test_reduce_mic_state_event(self):
        state = HudState(mic_mode="on")
        next_state = reduce_event(state, MicStateEvent(mode="sleeping"))
        self.assertEqual(next_state.mic_mode, "sleeping")
        self.assertEqual(next_state.get_status_text(), "SLEEPING")
        self.assertEqual(next_state.get_border_color(), constants.COLOR_MIC_SLEEPING)

    def test_reduce_recognition_event(self):
        state = HudState(max_history=3)
        ev1 = RecognitionEvent(phrase="git status", rule_name="IDETerminalRule", kind="cmd")
        s1 = reduce_event(state, ev1)
        self.assertEqual(len(s1.history), 1)
        self.assertEqual(s1.history[0].text, "git status")
        self.assertEqual(s1.voice.last_phrase, "git status")
        self.assertEqual(s1.voice.last_rule, "IDETerminalRule")

        # Add multiple events exceeding max_history (verify bounded circular buffer)
        s2 = reduce_event(s1, RecognitionEvent(phrase="cmd 2"))
        s3 = reduce_event(s2, RecognitionEvent(phrase="cmd 3"))
        s4 = reduce_event(s3, RecognitionEvent(phrase="cmd 4"))
        self.assertEqual(len(s4.history), 3)
        self.assertEqual(s4.history[0].text, "cmd 2")
        self.assertEqual(s4.history[2].text, "cmd 4")

    def test_reduce_active_rules_event(self):
        state = HudState()
        ev = ActiveRulesEvent(rules=["IDETerminalRule", "NavigationCCR"])
        next_state = reduce_event(state, ev)
        self.assertEqual(next_state.voice.active_rules, ("IDETerminalRule", "NavigationCCR"))

    def test_reduce_desktop_context_event(self):
        state = HudState()
        ev = DesktopContextEvent(
            process_name="code",
            window_title="hud.py - Caster",
            semantic_zone="IntegratedTerminal",
            active_file="hud.py"
        )
        next_state = reduce_event(state, ev)
        self.assertEqual(next_state.desktop_context.process_name, "code")
        self.assertEqual(next_state.desktop_context.semantic_zone, "IntegratedTerminal")

    def test_event_serialization_roundtrip(self):
        event = DesktopContextEvent(
            process_name="antigravity",
            window_title="IDE Workspace",
            semantic_zone="EditorCodeBuffer",
            active_file="state.py"
        )
        data = event.to_dict()
        self.assertEqual(data["event_type"], "desktop_context")
        deserialized = event_from_dict(data)
        self.assertIsInstance(deserialized, DesktopContextEvent)
        self.assertEqual(deserialized.process_name, "antigravity")
        self.assertEqual(deserialized.semantic_zone, "EditorCodeBuffer")

    def test_config_fallback_merger(self):
        user_cfg = {"theme": "frosted-dark", "custom_key": 123}
        merged = constants.merge_hud_config(user_cfg)
        self.assertEqual(merged["theme"], "frosted-dark")
        self.assertEqual(merged["status_border"], True)
        self.assertEqual(merged["port"], constants.DEFAULT_HUD_PORT)


if __name__ == "__main__":
    unittest.main()
