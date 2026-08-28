"""
Test dynamic border styling on QFrame container.
"""

import sys
import unittest
from castervoice.lib.qt import QtWidgets, QtCore
from castervoice.asynch.hud.core.state import HudState
from castervoice.asynch.hud.core import constants
from castervoice.asynch.hud.ui.widgets.border_controller import BorderController

app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication([])


class TestDynamicBorder(unittest.TestCase):
    def setUp(self):
        self.frame = QtWidgets.QFrame()
        self.frame.setObjectName("hud_container")
        self.frame.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.controller = BorderController(self.frame)

    def test_listening_state_green(self):
        state = HudState(mic_mode="on")
        self.controller.update_state(state)
        self.assertIn(constants.COLOR_MIC_ON, self.frame.styleSheet())

    def test_sleeping_state_red(self):
        state = HudState(mic_mode="sleeping")
        self.controller.update_state(state)
        self.assertIn(constants.COLOR_MIC_SLEEPING, self.frame.styleSheet())

    def test_drag_mode_amber(self):
        state = HudState(mic_mode="on", is_drag_mode=True)
        self.controller.update_state(state)
        self.assertIn(constants.COLOR_DRAG, self.frame.styleSheet())

    def test_framed_mode_preserves_border(self):
        state = HudState(mic_mode="on", frameless=False)
        self.controller.set_frameless(False)
        self.controller.update_state(state)
        self.assertIn(constants.COLOR_MIC_ON, self.frame.styleSheet())


if __name__ == "__main__":
    unittest.main()
