"""
HUD Theme Manager and QSS Stylesheet Presets.
Compatible with Python 2.7 and Python 3.x.
"""

import os

THEME_CLASSIC = "classic"
THEME_FROSTED = "frosted-dark"
THEME_MINIMAL = "minimal-transparent"
THEME_HIGH_CONTRAST = "high-contrast"

THEME_ALIASES = {
    "classic": THEME_CLASSIC,
    "light": THEME_CLASSIC,
    "frosted": THEME_FROSTED,
    "frosted-dark": THEME_FROSTED,
    "dark": THEME_FROSTED,
    "minimal": THEME_MINIMAL,
    "minimal-transparent": THEME_MINIMAL,
    "transparent": THEME_MINIMAL,
    "high-contrast": THEME_HIGH_CONTRAST,
    "contrast": THEME_HIGH_CONTRAST,
    "high contrast": THEME_HIGH_CONTRAST,
}

PRESET_THEMES = {
    THEME_CLASSIC: """
        QMainWindow, QWidget {
            background-color: #f0f0f0;
            color: #000000;
        }
        QTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: none;
            border-radius: 0px;
            font-family: 'Segoe UI', Arial, sans-serif;
            min-height: 0px;
            margin: 0px;
        }
        QTreeView, QListWidget {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #dcdcdc;
            selection-background-color: #3498db;
            selection-color: #ffffff;
        }
        QHeaderView::section {
            background-color: #e4e4e4;
            color: #000000;
            padding: 4px;
            border: 1px solid #dcdcdc;
            font-weight: bold;
        }
        QPushButton {
            background-color: #e0e0e0;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 4px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QLineEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 3px;
        }
        QMenu {
            background-color: #f0f0f0;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 4px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 9pt;
        }
        QMenu::item {
            background-color: transparent;
            padding: 5px 24px 5px 12px;
            border-radius: 2px;
        }
        QMenu::item:selected {
            background-color: #3498db;
            color: #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background-color: #dcdcdc;
            margin: 4px 6px;
        }
    """,
    THEME_FROSTED: """
        QMainWindow, QWidget {
            background-color: #1e1e24;
            color: #f8f9fa;
        }
        QTextEdit {
            background-color: #18181c;
            color: #e9ecef;
            border: none;
            border-radius: 0px;
            font-family: 'Segoe UI', Arial, sans-serif;
            min-height: 0px;
            margin: 0px;
        }
        QTreeView, QListWidget {
            background-color: #18181c;
            color: #e9ecef;
            border: 1px solid #2b2b36;
            selection-background-color: #4a5568;
            selection-color: #ffffff;
        }
        QHeaderView::section {
            background-color: #2b2b36;
            color: #60a5fa;
            padding: 4px;
            border: 1px solid #3b3b4a;
            font-weight: bold;
        }
        QPushButton {
            background-color: #2b2b36;
            color: #f8f9fa;
            border: 1px solid #3b3b4a;
            padding: 4px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #3b3b4a;
        }
        QLineEdit {
            background-color: #18181c;
            color: #f8f9fa;
            border: 1px solid #3b3b4a;
            padding: 3px;
        }
        QMenu {
            background-color: #1e1e24;
            color: #f8f9fa;
            border: 1px solid #3b3b4a;
            padding: 4px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 9pt;
        }
        QMenu::item {
            background-color: transparent;
            padding: 5px 24px 5px 12px;
            border-radius: 2px;
        }
        QMenu::item:selected {
            background-color: #2563eb;
            color: #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background-color: #3b3b4a;
            margin: 4px 6px;
        }
    """,
    THEME_MINIMAL: """
        QMainWindow, QWidget {
            background-color: #111111;
            color: #e0e0e0;
        }
        QTextEdit {
            background-color: #000000;
            color: #f5f5f5;
            border: none;
            border-radius: 0px;
            font-family: 'Segoe UI', Arial, sans-serif;
            min-height: 0px;
            margin: 0px;
        }
        QTreeView, QListWidget {
            background-color: #000000;
            color: #f5f5f5;
            border: 1px solid #333333;
            selection-background-color: #222222;
            selection-color: #3498db;
        }
        QHeaderView::section {
            background-color: #1a1a1a;
            color: #93c5fd;
            padding: 4px;
            border: 1px solid #333333;
            font-weight: bold;
        }
        QPushButton {
            background-color: #1a1a1a;
            color: #e0e0e0;
            border: 1px solid #333333;
            padding: 4px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #2a2a2a;
        }
        QLineEdit {
            background-color: #000000;
            color: #e0e0e0;
            border: 1px solid #333333;
            padding: 3px;
        }
        QMenu {
            background-color: #111111;
            color: #e0e0e0;
            border: 1px solid #333333;
            padding: 4px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 9pt;
        }
        QMenu::item {
            background-color: transparent;
            padding: 5px 24px 5px 12px;
            border-radius: 2px;
        }
        QMenu::item:selected {
            background-color: #2563eb;
            color: #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background-color: #333333;
            margin: 4px 6px;
        }
    """,
    THEME_HIGH_CONTRAST: """
        QMainWindow, QWidget {
            background-color: #000000;
            color: #ffffff;
        }
        QTextEdit {
            background-color: #000000;
            color: #ffffff;
            border: none;
            border-radius: 0px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-weight: bold;
            min-height: 0px;
            margin: 0px;
        }
        QTreeView, QListWidget {
            background-color: #000000;
            color: #ffffff;
            border: 2px solid #ffffff;
            selection-background-color: #ffffff;
            selection-color: #000000;
        }
        QHeaderView::section {
            background-color: #000000;
            color: #ffffff;
            padding: 4px;
            border: 2px solid #ffffff;
            font-weight: bold;
        }
        QPushButton {
            background-color: #000000;
            color: #ffffff;
            border: 2px solid #ffffff;
            padding: 4px 10px;
            border-radius: 0px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #ffffff;
            color: #000000;
        }
        QLineEdit {
            background-color: #000000;
            color: #ffffff;
            border: 2px solid #ffffff;
            padding: 3px;
        }
        QMenu {
            background-color: #000000;
            color: #ffffff;
            border: 2px solid #ffffff;
            padding: 4px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 9pt;
            font-weight: bold;
        }
        QMenu::item {
            background-color: transparent;
            padding: 5px 24px 5px 12px;
        }
        QMenu::item:selected {
            background-color: #ffffff;
            color: #000000;
            font-weight: bold;
        }
        QMenu::separator {
            height: 2px;
            background-color: #ffffff;
            margin: 4px 6px;
        }
    """,
}


class ThemeManager(object):
    """
    Manages HUD appearance themes and loads QSS stylesheets.
    """

    @classmethod
    def normalize_theme_name(cls, theme_name):
        """Converts user input/alias to canonical theme name."""
        if not theme_name:
            return THEME_CLASSIC
        cleaned = str(theme_name).lower().strip()
        return THEME_ALIASES.get(cleaned, THEME_CLASSIC)

    @classmethod
    def get_stylesheet(cls, theme_name):
        """Returns the complete QSS stylesheet string for the requested theme."""
        norm = cls.normalize_theme_name(theme_name)
        return PRESET_THEMES.get(norm, PRESET_THEMES[THEME_CLASSIC])

    @classmethod
    def get_available_themes(cls):
        """Returns a list of all canonical theme names."""
        return [THEME_CLASSIC, THEME_FROSTED, THEME_MINIMAL, THEME_HIGH_CONTRAST]
