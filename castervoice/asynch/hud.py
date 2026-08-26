#! python
'''
Caster HUD Window module
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

QApplication = QtWidgets.QApplication
QMainWindow = QtWidgets.QMainWindow
QTextEdit = QtWidgets.QTextEdit
QTreeView = QtWidgets.QTreeView
QVBoxLayout = QtWidgets.QVBoxLayout
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
TEXT_CURSOR_END = qt_attr(
    QtGui,
    ("QTextCursor", "End"),
    ("QTextCursor", "MoveOperation", "End"),
)

CLEAR_HUD_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
HIDE_HUD_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SHOW_HUD_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
HIDE_RULES_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SHOW_RULES_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))
SEND_COMMAND_EVENT = QtCore.QEvent.Type(QtCore.QEvent.registerEventType(-1))


def _create_hud_icon(app):
    """
    Create a crisp speech/caster icon for the system tray,
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

    def __init__(self, type, text):
        QtCore.QEvent.__init__(self, type)
        self._text = text

    @property
    def text(self):
        return self._text


class RulesWindow(QWidget):

    _WIDTH = 600
    _MARGIN = 30

    def __init__(self, text):
        use_tray = settings.settings(["hud", "system_tray"], default_value=False)
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


class HUDWindow(QMainWindow):

    _WIDTH = 300
    _HEIGHT = 200
    _MARGIN = 30

    def __init__(self, server):
        settings.initialize()
        self.use_tray = settings.settings(["hud", "system_tray"], default_value=False)
        flags = WINDOW_STAYS_ON_TOP_HINT
        if self.use_tray:
            flags |= TOOL_WINDOW_HINT
        QMainWindow.__init__(self, flags=flags)
        x = dragonfly.monitors[0].rectangle.dx - (HUDWindow._WIDTH + HUDWindow._MARGIN)
        y = HUDWindow._MARGIN
        dx = HUDWindow._WIDTH
        dy = HUDWindow._HEIGHT
        self.server = server
        self.setup_xmlrpc_server()
        self.setGeometry(x, y, dx, dy)
        self.setWindowTitle(settings.HUD_TITLE)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.setCentralWidget(self.output)
        self.rules_window = None
        self.commands_count = 0
        self.tray_icon = None
        self.toggle_action = None
        if self.use_tray:
            self.setup_tray_icon()

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
        QMainWindow.changeEvent(self, event)

    def event(self, event):
        if event.type() == SHOW_HUD_EVENT:
            self.show_and_raise()
            return True
        if event.type() == HIDE_HUD_EVENT:
            self.hide()
            return True
        if event.type() == SHOW_RULES_EVENT:
            self.rules_window = RulesWindow(event.text)
            self.rules_window.show()
            return True
        if event.type() == HIDE_RULES_EVENT and self.rules_window:
            self.rules_window.close()
            self.rules_window = None
            return True
        if event.type() == SEND_COMMAND_EVENT:
            escaped_text = html.escape(event.text)
            if escaped_text.startswith('$'):
                formatted_text = '<font color="blue">&lt;</font><b>{}</b>'.format(escaped_text[1:])
                if self.commands_count == 0:
                    self.output.setHtml(formatted_text)
                else:
                    # self.output.append('<br>')
                    self.output.append(formatted_text)
                cursor = self.output.textCursor()
                cursor.movePosition(TEXT_CURSOR_END)
                self.output.setTextCursor(cursor)
                self.output.ensureCursorVisible()
                self.commands_count += 1
                if self.commands_count == 50:
                    self.commands_count = 0
                return True
            if escaped_text.startswith('@'):
                formatted_text = '<font color="purple">&gt;</font><b>{}</b>'.format(escaped_text[1:])
            elif escaped_text.startswith(''):
                formatted_text = '<font color="red">&gt;</font>{}'.format(escaped_text)
            else:
                formatted_text = escaped_text
            self.output.append(formatted_text)
            cursor = self.output.textCursor()
            cursor.movePosition(TEXT_CURSOR_END)
            self.output.setTextCursor(cursor)
            self.output.ensureCursorVisible()
            return True
        if event.type() == CLEAR_HUD_EVENT:
            self.commands_count = 0
            return True
        return QMainWindow.event(self, event)

    def closeEvent(self, event):
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
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()


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


def handler(signum, frame):
    """
    This handler doesn't stop the application when ^C is pressed,
    but it prevents exceptions being thrown when later
    the application is terminated from GUI.  Normally, HUD is started
    by the recognition process and can't be killed from shell prompt,
    in which case this handler is not needed.
    """
    pass


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handler)
    server_address = (Communicator.LOCALHOST, Communicator().com_registry["hud"])
    # allow_none=True means Python constant None will be translated into XML
    server = SimpleXMLRPCServer(server_address, logRequests=False, allow_none=True)
    app = QApplication(sys.argv)
    window = HUDWindow(server)
    window.show()
    exit_code = qapp_exec(app)
    server.shutdown()
    sys.exit(exit_code)
