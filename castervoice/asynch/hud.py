#! python
'''
Caster HUD Window module (Object-Oriented, Modular, Themeable, Profiles, Frameless Resize, Drag Mode, System Tray)
'''
# pylint: disable=import-error,no-name-in-module
import html
import json
import os
import signal
import sys
import threading
import dragonfly
from xmlrpc.server import SimpleXMLRPCServer
try:  # Style C -- may be imported into Caster, or externally
    BASE_PATH = os.path.realpath(__file__).rsplit(os.path.sep + "castervoice", 1)[0]
    if BASE_PATH not in sys.path:
        sys.path.append(BASE_PATH)
finally:
    from castervoice.lib.merge.communication import Communicator
    from castervoice.lib import settings
    from castervoice.lib.qt import QtCore, QtGui, QtWidgets, qt_attr, qapp_exec
    from castervoice.asynch import hud_themes
    from castervoice.asynch.hud_profile import ProfileManager

QApplication = QtWidgets.QApplication
QMainWindow = QtWidgets.QMainWindow
QTextEdit = QtWidgets.QTextEdit
QTreeView = QtWidgets.QTreeView
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QListWidget = QtWidgets.QListWidget
QPushButton = QtWidgets.QPushButton
QWidget = QtWidgets.QWidget
QSystemTrayIcon = getattr(QtWidgets, "QSystemTrayIcon", None)
QMenu = getattr(QtWidgets, "QMenu", None)
QStyle = QtWidgets.QStyle
try:
    QAction = QtGui.QAction
except AttributeError:
    QAction = QtWidgets.QAction

WINDOW_STAYS_ON_TOP_HINT = qt_attr(
    QtCore,
    ("Qt", "WindowStaysOnTopHint"),
    ("Qt", "WindowType", "WindowStaysOnTopHint"),
)
TOOL_WINDOW_HINT = qt_attr(
    QtCore,
    ("Qt", "Tool"),
    ("Qt", "WindowType", "Tool"),
)
FRAMELESS_WINDOW_HINT = qt_attr(
    QtCore,
    ("Qt", "FramelessWindowHint"),
    ("Qt", "WindowType", "FramelessWindowHint"),
)
TEXT_CURSOR_END = qt_attr(
    QtGui,
    ("QTextCursor", "End"),
    ("QTextCursor", "MoveOperation", "End"),
)
SIZE_ALL_CURSOR = qt_attr(
    QtCore,
    ("Qt", "SizeAllCursor"),
    ("Qt", "CursorShape", "SizeAllCursor"),
)
SIZE_HOR_CURSOR = qt_attr(
    QtCore,
    ("Qt", "SizeHorCursor"),
    ("Qt", "CursorShape", "SizeHorCursor"),
)
SIZE_VER_CURSOR = qt_attr(
    QtCore,
    ("Qt", "SizeVerCursor"),
    ("Qt", "CursorShape", "SizeVerCursor"),
)
SIZE_FDIAG_CURSOR = qt_attr(
    QtCore,
    ("Qt", "SizeFDiagCursor"),
    ("Qt", "CursorShape", "SizeFDiagCursor"),
)
SIZE_BDIAG_CURSOR = qt_attr(
    QtCore,
    ("Qt", "SizeBDiagCursor"),
    ("Qt", "CursorShape", "SizeBDiagCursor"),
)
ARROW_CURSOR = qt_attr(
    QtCore,
    ("Qt", "ArrowCursor"),
    ("Qt", "CursorShape", "ArrowCursor"),
)

CLEAR_HUD_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
HIDE_HUD_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SHOW_HUD_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
HIDE_RULES_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SHOW_RULES_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SHOW_HELP_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
HIDE_HELP_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SHOW_PROFILE_DIALOG_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SEND_COMMAND_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SET_THEME_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
CYCLE_THEME_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
TOGGLE_BORDER_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
TOGGLE_DRAG_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
TOGGLE_SCROLLBAR_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
FONT_CHANGE_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SAVE_PROFILE_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
LOAD_PROFILE_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))


def _create_hud_icon(app):
    """
    Create a crisp 2D vector badge icon for the system tray,
    falling back to standard desktop icon.
    """
    try:
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(41, 128, 185))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
        painter.setPen(QtGui.QColor(255, 255, 255))
        font = QtGui.QFont("Arial", 14, QtGui.QFont.Bold)
        painter.setFont(font)
        painter.drawText(QtCore.QRect(0, 0, 32, 32), QtCore.Qt.AlignCenter, "C")
        painter.end()
        return QtGui.QIcon(pixmap)
    except Exception:
        if app is not None:
            return app.style().standardIcon(QStyle.SP_DesktopIcon)
        return QtGui.QIcon()


class RPCEvent(QtCore.QEvent):

    def __init__(self, type, text=""):
        QtCore.QEvent.__init__(self, type)
        self._text = text

    @property
    def text(self):
        return self._text


class ProfileDialog(QWidget):
    """
    Unified dialog for managing (Save, Load, Delete) named HUD profiles.
    Fully accessible via keyboard shortcuts: Enter (Save), L (Load), Del (Delete), Esc (Close).
    """

    _WIDTH = 400
    _HEIGHT = 320

    def __init__(self, hud_window, theme=hud_themes.THEME_CLASSIC, use_tray=False):
        flags = WINDOW_STAYS_ON_TOP_HINT
        if use_tray:
            flags |= TOOL_WINDOW_HINT
        QWidget.__init__(self, f=flags)
        self.hud_window = hud_window
        self.profile_mgr = hud_window.profile_mgr

        x = dragonfly.monitors[0].rectangle.dx - (ProfileDialog._WIDTH + 40)
        y = 200
        self.setGeometry(x, y, ProfileDialog._WIDTH, ProfileDialog._HEIGHT)
        self.setWindowTitle("Caster HUD Profiles")
        self.setStyleSheet(hud_themes.get_theme_stylesheet(theme))

        layout = QVBoxLayout()

        header = QLabel("<b>Caster HUD Profile Manager</b>")
        layout.addWidget(header)

        info_lbl = QLabel("Saved Profiles:")
        layout.addWidget(info_lbl)

        self.list_widget = QListWidget()
        self._populate_profiles()
        self.list_widget.currentTextChanged.connect(self._on_profile_selected)
        layout.addWidget(self.list_widget)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Profile Name:"))
        self.name_edit = QLineEdit("default")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save [Enter]")
        self.save_btn.clicked.connect(self._do_save)
        btn_layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("Load [L]")
        self.load_btn.clicked.connect(self._do_load)
        btn_layout.addWidget(self.load_btn)

        self.reset_btn = QPushButton("Reset Default [R]")
        self.reset_btn.clicked.connect(self._do_reset_default)
        btn_layout.addWidget(self.reset_btn)

        self.del_btn = QPushButton("Delete [Del]")
        self.del_btn.clicked.connect(self._do_delete)
        btn_layout.addWidget(self.del_btn)

        self.cancel_btn = QPushButton("Close [Esc]")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _populate_profiles(self):
        self.list_widget.clear()
        for p in self.profile_mgr.list_profiles():
            self.list_widget.addItem(p)

    def _on_profile_selected(self, text):
        if text:
            self.name_edit.setText(text)

    def _do_save(self):
        name = self.name_edit.text().strip()
        if name:
            self.hud_window.save_current_profile(name)
        self.close()

    def _do_load(self):
        name = self.name_edit.text().strip()
        if not name and self.list_widget.currentItem():
            name = self.list_widget.currentItem().text().strip()
        if name:
            self.hud_window.load_named_profile(name)
        self.close()

    def _do_reset_default(self):
        self.hud_window.reset_to_default_profile()
        self._populate_profiles()

    def _do_delete(self):
        name = self.name_edit.text().strip()
        if not name and self.list_widget.currentItem():
            name = self.list_widget.currentItem().text().strip()
        if name:
            self.profile_mgr.delete_profile(name)
            self._populate_profiles()

    def show_dialog(self, mode="save"):
        self._populate_profiles()
        self.show()
        self.raise_()
        self.activateWindow()
        if mode == "save":
            self.name_edit.setFocus()
            self.name_edit.selectAll()
        else:
            self.list_widget.setFocus()

    def keyPressEvent(self, event):
        key_esc = qt_attr(QtCore, ("Qt", "Key_Escape"), ("Qt", "Key", "Key_Escape"))
        key_del = qt_attr(QtCore, ("Qt", "Key_Delete"), ("Qt", "Key", "Key_Delete"))
        key_enter = qt_attr(QtCore, ("Qt", "Key_Return"), ("Qt", "Key", "Key_Return"))
        key_enter_pad = qt_attr(QtCore, ("Qt", "Key_Enter"), ("Qt", "Key", "Key_Enter"))
        key_l = qt_attr(QtCore, ("Qt", "Key_L"), ("Qt", "Key", "Key_L"))
        key_r = qt_attr(QtCore, ("Qt", "Key_R"), ("Qt", "Key", "Key_R"))

        if event.key() == key_esc:
            self.close()
            event.accept()
            return
        if event.key() == key_del:
            self._do_delete()
            event.accept()
            return
        if event.key() in (key_enter, key_enter_pad):
            self._do_save()
            event.accept()
            return
        if event.key() == key_l and not self.name_edit.hasFocus():
            self._do_load()
            event.accept()
            return
        if event.key() == key_r and not self.name_edit.hasFocus():
            self._do_reset_default()
            event.accept()
            return
        QWidget.keyPressEvent(self, event)


class HelpWindow(QWidget):
    """
    Standalone help dialog displaying organized Caster HUD voice commands.
    """

    _WIDTH = 540
    _HEIGHT = 460
    _MARGIN = 30

    def __init__(self, theme=hud_themes.THEME_CLASSIC, use_tray=False):
        flags = WINDOW_STAYS_ON_TOP_HINT
        if use_tray:
            flags |= TOOL_WINDOW_HINT
        QWidget.__init__(self, f=flags)

        x = dragonfly.monitors[0].rectangle.dx - (HelpWindow._WIDTH + HelpWindow._MARGIN)
        y = 250
        self.setGeometry(x, y, HelpWindow._WIDTH, HelpWindow._HEIGHT)
        self.setWindowTitle("Caster HUD - Commands & Help")
        self.setStyleSheet(hud_themes.get_theme_stylesheet(theme))

        layout = QVBoxLayout()

        help_view = QTextEdit()
        help_view.setReadOnly(True)
        help_view.setFont(QtGui.QFont("Segoe UI", 9))

        help_html = """
        <style>
            h3 { color: #3498db; margin-bottom: 2px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
            th { text-align: left; color: #60a5fa; border-bottom: 1px solid #374151; padding: 4px; font-weight: bold; }
            td { padding: 4px; border-bottom: 1px solid rgba(255,255,255,10); }
            code { color: #f59e0b; font-weight: bold; }
        </style>
        <h3>Visibility & Window Controls</h3>
        <table>
            <tr><th>Voice Command</th><th>Description</th></tr>
            <tr><td><code>show caster hud</code></td><td>Opens or restores the HUD window</td></tr>
            <tr><td><code>hide caster hud</code></td><td>Docks HUD into system tray / hides overlay</td></tr>
            <tr><td><code>clear caster hud</code></td><td>Clears HUD text output</td></tr>
            <tr><td><code>caster hud border toggle</code></td><td>Toggles title bar / frameless overlay (or press 'T')</td></tr>
            <tr><td><code>caster hud drag toggle</code></td><td>Toggles mouse & arrow key drag mode (or press 'D')</td></tr>
            <tr><td><code>caster hud scroll toggle</code></td><td>Toggles vertical scrollbar on/off</td></tr>
        </table>

        <h3>Themes & Appearance</h3>
        <table>
            <tr><th>Voice Command</th><th>Description</th></tr>
            <tr><td><code>caster hud theme</code></td><td>Cycles through available themes</td></tr>
            <tr><td><code>caster hud theme classic</code></td><td>Original upstream classic theme</td></tr>
            <tr><td><code>caster hud theme frosted</code></td><td>Modern acrylic dark theme</td></tr>
            <tr><td><code>caster hud theme minimal</code></td><td>Semi-transparent floating text overlay</td></tr>
            <tr><td><code>caster hud theme high contrast</code></td><td>Pure black with high-contrast text</td></tr>
        </table>

        <h3>Font Sizing</h3>
        <table>
            <tr><th>Voice Command</th><th>Description</th></tr>
            <tr><td><code>caster hud font increase</code></td><td>Increases font size by 1pt</td></tr>
            <tr><td><code>caster hud font decrease</code></td><td>Decreases font size by 1pt</td></tr>
            <tr><td><code>caster hud font reset</code></td><td>Resets font size to default 9pt</td></tr>
        </table>

        <h3>Profiles & Layouts</h3>
        <table>
            <tr><th>Voice Command</th><th>Description</th></tr>
            <tr><td><code>caster hud save profile</code></td><td>Opens Profile Dialog to save current layout [Enter]</td></tr>
            <tr><td><code>caster hud load profile</code></td><td>Opens Profile Dialog to load a saved profile [L]</td></tr>
        </table>
        """
        help_view.setHtml(help_html)
        layout.addWidget(help_view)

        close_btn = QPushButton("Close [Esc]")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def keyPressEvent(self, event):
        key_esc = qt_attr(QtCore, ("Qt", "Key_Escape"), ("Qt", "Key", "Key_Escape"))
        if event.key() == key_esc:
            self.close()
            event.accept()
            return
        QWidget.keyPressEvent(self, event)


class RulesWindow(QWidget):

    _WIDTH = 600
    _MARGIN = 30

    def __init__(self, text, theme=hud_themes.THEME_CLASSIC, use_tray=False):
        flags = WINDOW_STAYS_ON_TOP_HINT
        if use_tray:
            flags |= TOOL_WINDOW_HINT
        QWidget.__init__(self, f=flags)
        x = dragonfly.monitors[0].rectangle.dx - (RulesWindow._WIDTH + RulesWindow._MARGIN)
        y = 300
        dx = RulesWindow._WIDTH
        dy = dragonfly.monitors[0].rectangle.dy - (y + 2 * RulesWindow._MARGIN)
        self.setGeometry(x, y, dx, dy)
        self.setWindowTitle("Active Rules")
        self.setStyleSheet(hud_themes.get_theme_stylesheet(theme))

        rules_tree = QtGui.QStandardItemModel()
        rules_tree.setColumnCount(2)
        rules_tree.setHorizontalHeaderLabels(['phrase', 'action'])
        rules_dict = json.loads(text)
        rules = rules_tree.invisibleRootItem()
        for g in rules_dict:
            gram = QtGui.QStandardItem(g["name"]) if len(g["rules"]) > 1 else None
            for r in g["rules"]:
                rule = QtGui.QStandardItem(r["name"])
                rule.setRowCount(len(r["specs"]))
                rule.setColumnCount(2)
                row = 0
                for s in r["specs"]:
                    phrase, _, action = s.partition('::')
                    rule.setChild(row, 0, QtGui.QStandardItem(phrase))
                    rule.setChild(row, 1, QtGui.QStandardItem(action))
                    row += 1
                if gram is None:
                    rules.appendRow(rule)
                else:
                    gram.appendRow(rule)
            if gram:
                rules.appendRow(gram)
        tree_view = QTreeView(self)
        tree_view.setModel(rules_tree)
        tree_view.setColumnWidth(0, RulesWindow._WIDTH // 2)
        layout = QVBoxLayout()
        layout.addWidget(tree_view)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        key_esc = qt_attr(QtCore, ("Qt", "Key_Escape"), ("Qt", "Key", "Key_Escape"))
        if event.key() == key_esc:
            self.close()
            event.accept()
            return
        QWidget.keyPressEvent(self, event)


class HUDWindow(QMainWindow):

    _DEFAULT_WIDTH = 300
    _DEFAULT_HEIGHT = 200
    _MARGIN = 30
    _DEFAULT_FONT_SIZE = 9
    _EDGE_MARGIN = 6

    def __init__(self, server):
        settings.initialize()
        self.profile_mgr = ProfileManager()

        self.use_tray = settings.settings(["hud", "system_tray"], default_value=False)
        self.current_theme = settings.settings(["hud", "theme"], default_value=hud_themes.THEME_CLASSIC)
        self.frameless = bool(settings.settings(["hud", "frameless"], default_value=False))
        self.opacity = float(settings.settings(["hud", "opacity"], default_value=1.0))
        self.hide_scrollbars = bool(settings.settings(["hud", "hide_scrollbars"], default_value=False))
        self.font_family = str(settings.settings(["hud", "font_family"], default_value="Segoe UI"))
        self.font_size = int(settings.settings(["hud", "font_size"], default_value=HUDWindow._DEFAULT_FONT_SIZE))
        self.drag_mode = False
        self._resizing_edge = None
        self._resize_start_geom = None
        self._resize_start_pos = None

        flags = self._compute_flags()
        QMainWindow.__init__(self, flags=flags)

        # Restore geometry from settings or defaults
        default_x = dragonfly.monitors[0].rectangle.dx - (HUDWindow._DEFAULT_WIDTH + HUDWindow._MARGIN)
        default_y = HUDWindow._MARGIN
        x = int(settings.settings(["hud", "x"], default_value=default_x))
        y = int(settings.settings(["hud", "y"], default_value=default_y))
        dx = int(settings.settings(["hud", "width"], default_value=HUDWindow._DEFAULT_WIDTH))
        dy = int(settings.settings(["hud", "height"], default_value=HUDWindow._DEFAULT_HEIGHT))

        # Clamp coordinates so title bar is never hidden off the top of the screen
        min_y = 0 if self.frameless else 30
        if y < min_y:
            y = min_y

        self.server = server
        self.setup_xmlrpc_server()
        self.setMinimumSize(0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setMouseTracking(True)
        self.setGeometry(x, y, dx, dy)
        self.setWindowTitle(settings.HUD_TITLE)

        if self.opacity < 1.0:
            self.setWindowOpacity(max(0.2, min(1.0, self.opacity)))

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumSize(0, 0)
        self.output.setFrameStyle(0)
        self.output.document().setDocumentMargin(2)
        self.output.viewport().setMouseTracking(True)
        self.output.viewport().installEventFilter(self)

        no_focus = qt_attr(QtCore, ("Qt", "NoFocus"), ("Qt", "FocusPolicy", "NoFocus"))
        self.output.setFocusPolicy(no_focus)
        ignored_policy = qt_attr(
            QtWidgets,
            ("QSizePolicy", "Ignored"),
            ("QSizePolicy", "Policy", "Ignored"),
        )
        self.output.setSizePolicy(ignored_policy, ignored_policy)
        self._apply_font()
        self._apply_scrollbar_policy()

        self.setCentralWidget(self.output)
        self.rules_window = None
        self.help_window = None
        self.profile_dialog = None
        self.commands_count = 0
        self.tray_icon = None
        self.toggle_action = None
        self.apply_theme(self.current_theme)

        # Periodic stay on top timer to ensure visibility over taskbar
        self.top_timer = QtCore.QTimer(self)
        self.top_timer.timeout.connect(self._periodic_stay_on_top)
        self.top_timer.start(2000)

        if self.use_tray:
            self.setup_tray_icon()

    def _compute_flags(self):
        flags = WINDOW_STAYS_ON_TOP_HINT
        if self.use_tray:
            flags |= TOOL_WINDOW_HINT
        if self.frameless:
            flags |= FRAMELESS_WINDOW_HINT
        return flags

    def _apply_font(self):
        if self.current_theme == hud_themes.THEME_CLASSIC and self.font_size == HUDWindow._DEFAULT_FONT_SIZE:
            self.output.setFont(QApplication.font())
        else:
            hud_font = QtGui.QFont(self.font_family, self.font_size)
            self.output.setFont(hud_font)

    def _apply_scrollbar_policy(self):
        scrollbar_policy = qt_attr(
            QtCore,
            ("Qt", "ScrollBarAlwaysOff" if self.hide_scrollbars else "ScrollBarAsNeeded"),
            ("Qt", "ScrollBarPolicy", "ScrollBarAlwaysOff" if self.hide_scrollbars else "ScrollBarAsNeeded"),
        )
        self.output.setVerticalScrollBarPolicy(scrollbar_policy)
        self.output.setHorizontalScrollBarPolicy(scrollbar_policy)

    def _update_focus_style(self, active):
        if not self.frameless:
            return
        if active:
            if self.current_theme == hud_themes.THEME_HIGH_CONTRAST:
                self.output.setStyleSheet("QTextEdit { border: 2px solid #00ffff; }")
            else:
                self.output.setStyleSheet("QTextEdit { border: 1px solid #3498db; }")
        else:
            self.output.setStyleSheet("")

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        # Preserve exact geometry before stylesheet application
        x = self.x()
        y = self.y()
        w = self.width()
        h = self.height()
        stylesheet = hud_themes.get_theme_stylesheet(theme_name)
        self.setStyleSheet(stylesheet)
        self._apply_font()
        self._update_focus_style(self.isActiveWindow())
        self.setMinimumSize(0, 0)
        self.output.setMinimumSize(0, 0)
        self.setGeometry(x, y, w, h)
        self.resize(w, h)
        if self.rules_window:
            self.rules_window.setStyleSheet(stylesheet)
        if self.help_window:
            self.help_window.setStyleSheet(stylesheet)
        if self.profile_dialog:
            self.profile_dialog.setStyleSheet(stylesheet)

    def cycle_theme(self):
        themes = hud_themes.get_available_themes()
        if self.current_theme in themes:
            idx = (themes.index(self.current_theme) + 1) % len(themes)
            next_theme = themes[idx]
        else:
            next_theme = hud_themes.THEME_CLASSIC
        self.apply_theme(next_theme)
        self._save_setting("theme", next_theme)
        self._append_system_msg("Theme: {}".format(next_theme.replace("-", " ").title()))

    def toggle_border(self):
        self.frameless = not self.frameless
        self._save_setting("frameless", self.frameless)
        
        # Save exact screen coordinates of client content area
        client_pos = self.mapToGlobal(QtCore.QPoint(0, 0))
        w = self.width()
        h = self.height()
        
        self.setWindowFlags(self._compute_flags())
        self.setMinimumSize(0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(client_pos.x(), client_pos.y(), w, h)
        self.resize(w, h)
        self.show()
        state_str = "Frameless" if self.frameless else "Title Bar (Framed)"
        self._append_system_msg("HUD Window: {}".format(state_str))

    def toggle_drag_mode(self):
        self.drag_mode = not self.drag_mode
        if self.drag_mode:
            self.setCursor(SIZE_ALL_CURSOR)
            self._append_system_msg("Drag Mode: Enabled (Click anywhere or Arrow Keys to move, press 'D' to lock)")
        else:
            self.unsetCursor()
            self._append_system_msg("Drag Mode: Locked")

    def toggle_scrollbars(self):
        self.hide_scrollbars = not self.hide_scrollbars
        self._save_setting("hide_scrollbars", self.hide_scrollbars)
        self._apply_scrollbar_policy()
        state_str = "Hidden" if self.hide_scrollbars else "Visible"
        self._append_system_msg("Scrollbars: {}".format(state_str))

    def font_increase(self):
        self.font_size = min(36, self.font_size + 1)
        self._apply_font()
        self._save_setting("font_size", self.font_size)

    def font_decrease(self):
        self.font_size = max(6, self.font_size - 1)
        self._apply_font()
        self._save_setting("font_size", self.font_size)

    def font_reset(self):
        self.font_size = HUDWindow._DEFAULT_FONT_SIZE
        self._apply_font()
        self._save_setting("font_size", self.font_size)
        self._append_system_msg("Font Size: {}pt".format(self.font_size))

    def save_current_profile(self, name="default"):
        profile_name = str(name).strip().lower() if name else "default"
        state = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "theme": self.current_theme,
            "frameless": self.frameless,
            "font_size": self.font_size,
            "opacity": self.opacity,
            "hide_scrollbars": self.hide_scrollbars,
        }
        self.profile_mgr.save_profile(profile_name, state)
        self._save_setting("x", self.x())
        self._save_setting("y", self.y())
        self._save_setting("width", self.width())
        self._save_setting("height", self.height())
        self._append_system_msg("Profile Saved: '{}'".format(profile_name))

    def load_named_profile(self, name="default"):
        profile_name = str(name).strip().lower() if name else "default"
        state = self.profile_mgr.load_profile(profile_name)
        if not state:
            self._append_system_msg("Profile '{}' not found".format(profile_name))
            return
        x = state.get("x", self.x())
        y = state.get("y", self.y())
        w = state.get("width", self.width())
        h = state.get("height", self.height())

        if "theme" in state:
            self.apply_theme(state["theme"])
            self._save_setting("theme", state["theme"])
        if "font_size" in state:
            self.font_size = state["font_size"]
            self._apply_font()
            self._save_setting("font_size", self.font_size)
        if "frameless" in state and state["frameless"] != self.frameless:
            self.frameless = state["frameless"]
            self._save_setting("frameless", self.frameless)
            self.setWindowFlags(self._compute_flags())
        if "hide_scrollbars" in state:
            self.hide_scrollbars = state["hide_scrollbars"]
            self._apply_scrollbar_policy()
            self._save_setting("hide_scrollbars", self.hide_scrollbars)

        self.setMinimumSize(0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(x, y, w, h)
        self.resize(w, h)
        self.show()
        self._append_system_msg("Profile Loaded: '{}'".format(profile_name))

    def reset_to_default_profile(self):
        default_x = dragonfly.monitors[0].rectangle.dx - (HUDWindow._DEFAULT_WIDTH + HUDWindow._MARGIN)
        default_y = HUDWindow._MARGIN
        default_state = {
            "x": default_x,
            "y": default_y,
            "width": HUDWindow._DEFAULT_WIDTH,
            "height": HUDWindow._DEFAULT_HEIGHT,
            "theme": hud_themes.THEME_CLASSIC,
            "frameless": False,
            "font_size": HUDWindow._DEFAULT_FONT_SIZE,
            "opacity": 1.0,
            "hide_scrollbars": False,
        }
        self.profile_mgr.save_profile("default", default_state)
        self.load_named_profile("default")
        self._append_system_msg("Default Profile Reset to Top-Right Classic")

    def show_profile_dialog(self, mode="save"):
        if self.profile_dialog is None:
            self.profile_dialog = ProfileDialog(self, theme=self.current_theme, use_tray=self.use_tray)
        self.profile_dialog.show_dialog(mode=mode)

    def show_help_dialog(self):
        if self.help_window is None:
            self.help_window = HelpWindow(theme=self.current_theme, use_tray=self.use_tray)
        self.help_window.show()
        self.help_window.raise_()
        self.help_window.activateWindow()

    def hide_help_dialog(self):
        if self.help_window:
            self.help_window.close()
            self.help_window = None

    def _periodic_stay_on_top(self):
        if self.isVisible() and not self.isMinimized():
            self.raise_()

    def _append_system_msg(self, text):
        formatted = '<font color="#9b59b6">&gt;</font><i>{}</i>'.format(html.escape(text))
        self.output.append(formatted)
        self._scroll_to_end()

    def _scroll_to_end(self):
        cursor = self.output.textCursor()
        cursor.movePosition(TEXT_CURSOR_END)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _save_setting(self, key, value):
        try:
            if settings.SETTINGS is not None:
                if "hud" not in settings.SETTINGS:
                    settings.SETTINGS["hud"] = {}
                settings.SETTINGS["hud"][key] = value
                settings.save_config()
        except Exception:
            pass

    # Frameless Edge Detection & Resize Logic
    def _detect_edge(self, pos):
        if not self.frameless:
            return None
        m = self._EDGE_MARGIN
        w = self.width()
        h = self.height()
        x = pos.x()
        y = pos.y()

        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m

        if top and left:
            return "top-left"
        if top and right:
            return "top-right"
        if bottom and left:
            return "bottom-left"
        if bottom and right:
            return "bottom-right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return None

    def _update_cursor_for_edge(self, edge):
        if self.drag_mode:
            self.setCursor(SIZE_ALL_CURSOR)
            return
        if edge in ("top-left", "bottom-right"):
            self.setCursor(SIZE_FDIAG_CURSOR)
        elif edge in ("top-right", "bottom-left"):
            self.setCursor(SIZE_BDIAG_CURSOR)
        elif edge in ("left", "right"):
            self.setCursor(SIZE_HOR_CURSOR)
        elif edge in ("top", "bottom"):
            self.setCursor(SIZE_VER_CURSOR)
        else:
            self.unsetCursor()

    # Event Filter for QTextEdit viewport to allow Dragging / Resizing anywhere inside
    def eventFilter(self, obj, event):
        left_btn = qt_attr(QtCore, ("Qt", "LeftButton"), ("Qt", "MouseButton", "LeftButton"))
        if obj == self.output.viewport():
            if event.type() == QtCore.QEvent.MouseMove:
                global_pos = event.globalPos()
                pos = self.mapFromGlobal(global_pos)
                if self.drag_mode and event.buttons() == left_btn and hasattr(self, "_drag_pos"):
                    self.move(global_pos - self._drag_pos)
                    return True
                if self._resizing_edge and event.buttons() == left_btn:
                    self._handle_resize(global_pos)
                    return True
                edge = self._detect_edge(pos)
                self._update_cursor_for_edge(edge)
            elif event.type() == QtCore.QEvent.MouseButtonPress and event.button() == left_btn:
                global_pos = event.globalPos()
                pos = self.mapFromGlobal(global_pos)
                edge = self._detect_edge(pos)
                if edge:
                    self._resizing_edge = edge
                    self._resize_start_geom = self.geometry()
                    self._resize_start_pos = global_pos
                    return True
                if self.drag_mode:
                    self._drag_pos = global_pos - self.frameGeometry().topLeft()
                    return True
            elif event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == left_btn:
                self._resizing_edge = None
                self._drag_pos = None
        return QMainWindow.eventFilter(self, obj, event)

    def _handle_resize(self, global_pos):
        if not self._resizing_edge or not self._resize_start_geom:
            return
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()
        g = self._resize_start_geom
        new_x, new_y, new_w, new_h = g.x(), g.y(), g.width(), g.height()

        if "right" in self._resizing_edge:
            new_w = max(50, g.width() + dx)
        if "bottom" in self._resizing_edge:
            new_h = max(20, g.height() + dy)
        if "left" in self._resizing_edge:
            actual_w = max(50, g.width() - dx)
            new_x = g.x() + (g.width() - actual_w)
            new_w = actual_w
        if "top" in self._resizing_edge:
            actual_h = max(20, g.height() - dy)
            new_y = g.y() + (g.height() - actual_h)
            new_h = actual_h

        self.setGeometry(new_x, new_y, new_w, new_h)

    def mousePressEvent(self, event):
        left_btn = qt_attr(QtCore, ("Qt", "LeftButton"), ("Qt", "MouseButton", "LeftButton"))
        if event.button() == left_btn:
            edge = self._detect_edge(event.pos())
            if edge:
                self._resizing_edge = edge
                self._resize_start_geom = self.geometry()
                self._resize_start_pos = event.globalPos()
                event.accept()
                return
            if self.drag_mode:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return
        QMainWindow.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        left_btn = qt_attr(QtCore, ("Qt", "LeftButton"), ("Qt", "MouseButton", "LeftButton"))
        if self._resizing_edge and event.buttons() == left_btn:
            self._handle_resize(event.globalPos())
            event.accept()
            return
        if self.drag_mode and event.buttons() == left_btn and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        edge = self._detect_edge(event.pos())
        self._update_cursor_for_edge(edge)
        QMainWindow.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        self._resizing_edge = None
        self._drag_pos = None
        QMainWindow.mouseReleaseEvent(self, event)

    def keyPressEvent(self, event):
        key_t = qt_attr(QtCore, ("Qt", "Key_T"), ("Qt", "Key", "Key_T"))
        key_d = qt_attr(QtCore, ("Qt", "Key_D"), ("Qt", "Key", "Key_D"))
        key_esc = qt_attr(QtCore, ("Qt", "Key_Escape"), ("Qt", "Key", "Key_Escape"))
        key_left = qt_attr(QtCore, ("Qt", "Key_Left"), ("Qt", "Key", "Key_Left"))
        key_right = qt_attr(QtCore, ("Qt", "Key_Right"), ("Qt", "Key", "Key_Right"))
        key_up = qt_attr(QtCore, ("Qt", "Key_Up"), ("Qt", "Key", "Key_Up"))
        key_down = qt_attr(QtCore, ("Qt", "Key_Down"), ("Qt", "Key", "Key_Down"))

        shift = bool(event.modifiers() & qt_attr(QtCore, ("Qt", "ShiftModifier"), ("Qt", "KeyboardModifier", "ShiftModifier")))
        step = 10 if shift else 1

        if event.key() == key_t:
            self.toggle_border()
            event.accept()
            return
        if event.key() == key_d:
            self.toggle_drag_mode()
            event.accept()
            return
        if event.key() == key_esc and self.drag_mode:
            self.toggle_drag_mode()
            event.accept()
            return

        if self.drag_mode:
            if event.key() == key_left:
                self.move(self.x() - step, self.y())
                event.accept()
                return
            if event.key() == key_right:
                self.move(self.x() + step, self.y())
                event.accept()
                return
            if event.key() == key_up:
                self.move(self.x(), self.y() - step)
                event.accept()
                return
            if event.key() == key_down:
                self.move(self.x(), self.y() + step)
                event.accept()
                return

        QMainWindow.keyPressEvent(self, event)

    def setup_tray_icon(self):
        if QSystemTrayIcon is None or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
        app = QApplication.instance()
        icon = _create_hud_icon(app)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip(settings.HUD_TITLE)

        if QMenu is not None:
            tray_menu = QMenu(self)
            self.toggle_action = QAction("Hide HUD", self)
            self.toggle_action.triggered.connect(self.toggle_visibility)
            tray_menu.addAction(self.toggle_action)

            clear_action = QAction("Clear HUD", self)
            clear_action.triggered.connect(self.xmlrpc_clear)
            tray_menu.addAction(clear_action)

            # Themes Submenu
            themes_menu = tray_menu.addMenu("Themes")
            for theme_key in hud_themes.get_available_themes():
                action_name = theme_key.replace("-", " ").title()
                theme_act = QAction(action_name, self)
                theme_act.triggered.connect(lambda checked=False, t=theme_key: (self.apply_theme(t), self._save_setting("theme", t)))
                themes_menu.addAction(theme_act)

            # Profiles Submenu
            profiles_menu = tray_menu.addMenu("Profiles")
            save_prof_act = QAction("Save Profile... [Enter]", self)
            save_prof_act.triggered.connect(lambda: self.show_profile_dialog("save"))
            profiles_menu.addAction(save_prof_act)

            load_prof_act = QAction("Load Profile... [L]", self)
            load_prof_act.triggered.connect(lambda: self.show_profile_dialog("load"))
            profiles_menu.addAction(load_prof_act)

            # Options Submenu
            opts_menu = tray_menu.addMenu("Options")
            border_act = QAction("Toggle Title Bar (T)", self)
            border_act.triggered.connect(self.toggle_border)
            opts_menu.addAction(border_act)

            drag_act = QAction("Toggle Drag Mode (D)", self)
            drag_act.triggered.connect(self.toggle_drag_mode)
            opts_menu.addAction(drag_act)

            scroll_act = QAction("Toggle Scrollbars", self)
            scroll_act.triggered.connect(self.toggle_scrollbars)
            opts_menu.addAction(scroll_act)

            # Help Action
            help_act = QAction("Help & Commands", self)
            help_act.triggered.connect(self.show_help_dialog)
            tray_menu.addAction(help_act)

            tray_menu.addSeparator()

            exit_action = QAction("Exit", self)
            exit_action.triggered.connect(self.xmlrpc_kill)
            tray_menu.addAction(exit_action)

            self.tray_icon.setContextMenu(tray_menu)

        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        trigger_val = qt_attr(
            QtWidgets,
            ("QSystemTrayIcon", "Trigger"),
            ("QSystemTrayIcon", "ActivationReason", "Trigger"),
        )
        double_click_val = qt_attr(
            QtWidgets,
            ("QSystemTrayIcon", "DoubleClick"),
            ("QSystemTrayIcon", "ActivationReason", "DoubleClick"),
        )
        if reason in (trigger_val, double_click_val):
            self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.show_and_raise()

    def show_and_raise(self):
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event):
        if self.toggle_action:
            self.toggle_action.setText("Hide HUD")
        QMainWindow.showEvent(self, event)

    def hideEvent(self, event):
        if self.toggle_action:
            self.toggle_action.setText("Show HUD")
        QMainWindow.hideEvent(self, event)

    def changeEvent(self, event):
        if self.use_tray and event.type() == QtCore.QEvent.WindowStateChange:
            if self.isMinimized() and self.tray_icon and self.tray_icon.isVisible():
                QtCore.QTimer.singleShot(0, self.hide)
                event.accept()
                return
        if event.type() == QtCore.QEvent.ActivationChange:
            self._update_focus_style(self.isActiveWindow())
        QMainWindow.changeEvent(self, event)

    def event(self, event):
        if event.type() == SHOW_HUD_EVENT:
            self.show_and_raise()
            return True
        if event.type() == HIDE_HUD_EVENT:
            self.hide()
            return True
        if event.type() == SHOW_RULES_EVENT:
            self.rules_window = RulesWindow(event.text, theme=self.current_theme, use_tray=self.use_tray)
            self.rules_window.show()
            return True
        if event.type() == HIDE_RULES_EVENT and self.rules_window:
            self.rules_window.close()
            self.rules_window = None
            return True
        if event.type() == SHOW_HELP_EVENT:
            self.show_help_dialog()
            return True
        if event.type() == HIDE_HELP_EVENT:
            self.hide_help_dialog()
            return True
        if event.type() == SHOW_PROFILE_DIALOG_EVENT:
            mode = getattr(event, "text", "save") or "save"
            self.show_profile_dialog(mode)
            return True
        if event.type() == SET_THEME_EVENT:
            self.apply_theme(event.text)
            self._save_setting("theme", event.text)
            return True
        if event.type() == CYCLE_THEME_EVENT:
            self.cycle_theme()
            return True
        if event.type() == TOGGLE_BORDER_EVENT:
            self.toggle_border()
            return True
        if event.type() == TOGGLE_DRAG_EVENT:
            self.toggle_drag_mode()
            return True
        if event.type() == TOGGLE_SCROLLBAR_EVENT:
            self.toggle_scrollbars()
            return True
        if event.type() == FONT_CHANGE_EVENT:
            action = getattr(event, "text", "")
            if action == "increase":
                self.font_increase()
            elif action == "decrease":
                self.font_decrease()
            elif action == "reset":
                self.font_reset()
            return True
        if event.type() == SAVE_PROFILE_EVENT:
            self.save_current_profile(event.text)
            return True
        if event.type() == LOAD_PROFILE_EVENT:
            self.load_named_profile(event.text)
            return True
        if event.type() == SEND_COMMAND_EVENT:
            escaped_text = html.escape(event.text)
            if self.current_theme == hud_themes.THEME_CLASSIC:
                blue_col = "blue"
                purple_col = "purple"
                red_col = "red"
            else:
                blue_col = "#3498db"
                purple_col = "#9b59b6"
                red_col = "#e74c3c"

            if escaped_text.startswith('$'):
                formatted_text = '<font color="{}">&lt;</font><b>{}</b>'.format(blue_col, escaped_text[1:])
                if self.commands_count == 0:
                    self.output.setHtml(formatted_text)
                else:
                    self.output.append(formatted_text)
                self._scroll_to_end()
                self.commands_count += 1
                if self.commands_count == 50:
                    self.commands_count = 0
                return True
            if escaped_text.startswith('@'):
                formatted_text = '<font color="{}">&gt;</font><b>{}</b>'.format(purple_col, escaped_text[1:])
            elif escaped_text.startswith(''):
                formatted_text = '<font color="{}">&gt;</font>{}'.format(red_col, escaped_text)
            else:
                formatted_text = escaped_text
            self.output.append(formatted_text)
            self._scroll_to_end()
            return True
        if event.type() == CLEAR_HUD_EVENT:
            self.commands_count = 0
            return True
        return QMainWindow.event(self, event)

    def closeEvent(self, event):
        self.save_current_profile("default")
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()
        event.accept()

    def setup_xmlrpc_server(self):
        self.server.register_function(self.xmlrpc_clear, "clear_hud")
        self.server.register_function(self.xmlrpc_ping, "ping")
        self.server.register_function(self.xmlrpc_hide_hud, "hide_hud")
        self.server.register_function(self.xmlrpc_hide_rules, "hide_rules")
        self.server.register_function(self.xmlrpc_kill, "kill")
        self.server.register_function(self.xmlrpc_send, "send")
        self.server.register_function(self.xmlrpc_show_hud, "show_hud")
        self.server.register_function(self.xmlrpc_show_rules, "show_rules")
        self.server.register_function(self.xmlrpc_set_theme, "set_theme")
        self.server.register_function(self.xmlrpc_cycle_theme, "cycle_theme")
        self.server.register_function(self.xmlrpc_toggle_border, "toggle_border")
        self.server.register_function(self.xmlrpc_toggle_drag, "toggle_drag")
        self.server.register_function(self.xmlrpc_toggle_scrollbars, "toggle_scrollbars")
        self.server.register_function(self.xmlrpc_font_increase, "font_increase")
        self.server.register_function(self.xmlrpc_font_decrease, "font_decrease")
        self.server.register_function(self.xmlrpc_font_reset, "font_reset")
        self.server.register_function(self.xmlrpc_save_profile, "save_profile")
        self.server.register_function(self.xmlrpc_load_profile, "load_profile")
        self.server.register_function(self.xmlrpc_reset_default_profile, "reset_default_profile")
        self.server.register_function(self.xmlrpc_show_profile_dialog, "show_profile_dialog")
        self.server.register_function(self.xmlrpc_show_help, "show_help")
        self.server.register_function(self.xmlrpc_hide_help, "hide_help")
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def xmlrpc_reset_default_profile(self):
        self.reset_to_default_profile()
        return 0

    def xmlrpc_clear(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(CLEAR_HUD_EVENT))
        return 0

    def xmlrpc_ping(self):
        return 0

    def xmlrpc_hide_hud(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(HIDE_HUD_EVENT))
        return 0

    def xmlrpc_show_hud(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(SHOW_HUD_EVENT))
        return 0

    def xmlrpc_hide_rules(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(HIDE_RULES_EVENT))
        return 0

    def xmlrpc_kill(self):
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def xmlrpc_send(self, text):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(SEND_COMMAND_EVENT, text))
        return len(text)

    def xmlrpc_show_rules(self, text):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(SHOW_RULES_EVENT, text))
        return len(text)

    def xmlrpc_set_theme(self, theme_name):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(SET_THEME_EVENT, theme_name))
        return 0

    def xmlrpc_cycle_theme(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(CYCLE_THEME_EVENT))
        return 0

    def xmlrpc_toggle_border(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(TOGGLE_BORDER_EVENT))
        return 0

    def xmlrpc_toggle_drag(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(TOGGLE_DRAG_EVENT))
        return 0

    def xmlrpc_toggle_scrollbars(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(TOGGLE_SCROLLBAR_EVENT))
        return 0

    def xmlrpc_font_increase(self):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(FONT_CHANGE_EVENT, "increase"))
        return 0

    def xmlrpc_font_decrease(self):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(FONT_CHANGE_EVENT, "decrease"))
        return 0

    def xmlrpc_font_reset(self):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(FONT_CHANGE_EVENT, "reset"))
        return 0

    def xmlrpc_save_profile(self, name="default"):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(SAVE_PROFILE_EVENT, name))
        return 0

    def xmlrpc_load_profile(self, name="default"):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(LOAD_PROFILE_EVENT, name))
        return 0

    def xmlrpc_show_profile_dialog(self, mode="save"):
        QtCore.QCoreApplication.postEvent(self, RPCEvent(SHOW_PROFILE_DIALOG_EVENT, mode))
        return 0

    def xmlrpc_show_help(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(SHOW_HELP_EVENT))
        return 0

    def xmlrpc_hide_help(self):
        QtCore.QCoreApplication.postEvent(self, QtCore.QEvent(HIDE_HELP_EVENT))
        return 0


def handler(signum, frame):
    """
    Prevents exceptions on signal termination.
    """
    pass


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handler)
    server_address = (Communicator.LOCALHOST, Communicator().com_registry["hud"])
    server = SimpleXMLRPCServer(server_address, logRequests=False, allow_none=True)
    app = QApplication(sys.argv)
    window = HUDWindow(server)
    window.show()
    exit_code = qapp_exec(app)
    server.shutdown()
    sys.exit(exit_code)
