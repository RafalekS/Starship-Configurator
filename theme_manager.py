"""
Theme manager for loading and applying color themes to the application.
Converts terminal color schemes to Qt stylesheets.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class ThemeManager:
    """Manages application themes and stylesheet generation"""

    def __init__(self, themes_file: str = "themes/themes.json"):
        """
        Initialize theme manager.

        Args:
            themes_file: Path to themes JSON file
        """
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        self.themes_file = script_dir / themes_file
        self.themes: Dict = {}
        self.current_theme: Optional[str] = None
        self._load_themes()

    def _load_themes(self):
        """Load themes from JSON file"""
        try:
            with open(self.themes_file, 'r', encoding='utf-8') as f:
                self.themes = json.load(f)
            print(f"Loaded {len(self.themes)} themes from {self.themes_file}")
        except FileNotFoundError:
            print(f"Themes file not found: {self.themes_file}")
            self.themes = {}
        except json.JSONDecodeError as e:
            print(f"Invalid themes JSON: {e}")
            self.themes = {}

    def get_theme_names(self) -> List[str]:
        """
        Get list of available theme names.

        Returns:
            List of theme names sorted alphabetically
        """
        return sorted(self.themes.keys())

    def get_theme(self, theme_name: str) -> Optional[Dict]:
        """
        Get theme data by name.

        Args:
            theme_name: Name of the theme

        Returns:
            Theme data dictionary or None if not found
        """
        return self.themes.get(theme_name)

    def generate_stylesheet(self, theme_name: str) -> str:
        """
        Generate Qt stylesheet from theme.

        Args:
            theme_name: Name of the theme to use

        Returns:
            Qt stylesheet string
        """
        theme = self.get_theme(theme_name)
        if not theme:
            print(f"Theme '{theme_name}' not found, using default")
            return ""

        self.current_theme = theme_name

        # Extract colors
        bg = theme.get('background', '#FFFFFF')
        fg = theme.get('foreground', '#000000')
        selection = theme.get('selection', '#3399FF')

        # Use bright colors for accents
        accent = theme.get('blue', '#0078D7')
        bright_accent = theme.get('brightBlue', '#4DA6FF')
        success = theme.get('green', '#00AA00')
        warning = theme.get('yellow', '#FFAA00')
        error = theme.get('red', '#CC0000')

        # Border and secondary colors
        border = theme.get('brightBlack', '#666666')
        disabled = theme.get('brightBlack', '#888888')

        # Generate comprehensive stylesheet
        stylesheet = f"""
/* Main Window */
QMainWindow {{
    background-color: {bg};
    color: {fg};
}}

/* Central Widget */
QWidget {{
    background-color: {bg};
    color: {fg};
}}

/* GroupBox */
QGroupBox {{
    background-color: {bg};
    color: {fg};
    border: 1px solid {border};
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: {accent};
}}

/* Labels */
QLabel {{
    color: {fg};
    background-color: transparent;
}}

/* Line Edit (Text Input) */
QLineEdit {{
    background-color: {theme.get('black', '#1E1E1E')};
    color: {fg};
    border: 1px solid {border};
    border-radius: 3px;
    padding: 5px;
    selection-background-color: {selection};
}}

QLineEdit:focus {{
    border: 1px solid {accent};
}}

QLineEdit:read-only {{
    background-color: {theme.get('brightBlack', '#2A2A2A')};
    color: {theme.get('brightWhite', fg)};
}}

/* Push Buttons */
QPushButton {{
    background-color: {accent};
    color: {theme.get('white', '#FFFFFF')};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {bright_accent};
}}

QPushButton:pressed {{
    background-color: {theme.get('brightCyan', accent)};
}}

QPushButton:disabled {{
    background-color: {disabled};
    color: {theme.get('brightBlack', '#666666')};
}}

/* QSpinBox */
QSpinBox {{
    background-color: {theme.get('black', '#1E1E1E')};
    color: {fg};
    border: 1px solid {border};
    border-radius: 3px;
    padding: 5px;
    selection-background-color: {selection};
}}

QSpinBox:focus {{
    border: 1px solid {accent};
}}

QSpinBox::up-button {{
    background-color: {theme.get('brightBlack', '#2A2A2A')};
    border: none;
    border-radius: 2px;
    width: 16px;
}}

QSpinBox::up-button:hover {{
    background-color: {accent};
}}

QSpinBox::down-button {{
    background-color: {theme.get('brightBlack', '#2A2A2A')};
    border: none;
    border-radius: 2px;
    width: 16px;
}}

QSpinBox::down-button:hover {{
    background-color: {accent};
}}

QSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 4px solid {fg};
    margin: 2px;
}}

QSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {fg};
    margin: 2px;
}}

/* QCheckBox */
QCheckBox {{
    color: {fg};
    spacing: 5px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {border};
    border-radius: 3px;
    background-color: {theme.get('black', '#1E1E1E')};
}}

QCheckBox::indicator:hover {{
    border: 2px solid {accent};
}}

QCheckBox::indicator:checked {{
    background-color: {accent};
    border: 2px solid {accent};
}}

QCheckBox::indicator:checked:hover {{
    background-color: {bright_accent};
    border: 2px solid {bright_accent};
}}

QCheckBox::indicator:disabled {{
    background-color: {disabled};
    border: 2px solid {disabled};
}}

/* QListWidget Checkboxes */
QListWidget::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {border};
    border-radius: 3px;
    background-color: {theme.get('black', '#1E1E1E')};
}}

QListWidget::indicator:hover {{
    border: 2px solid {accent};
}}

QListWidget::indicator:checked {{
    background-color: {accent};
    border: 2px solid {accent};
}}

QListWidget::indicator:checked:hover {{
    background-color: {bright_accent};
    border: 2px solid {bright_accent};
}}

/* Combo Box */
QComboBox {{
    background-color: {theme.get('black', '#1E1E1E')};
    color: {fg};
    border: 1px solid {border};
    border-radius: 3px;
    padding: 5px;
}}

QComboBox:hover {{
    border: 1px solid {accent};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 5px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {fg};
    margin-right: 5px;
}}

QComboBox QAbstractItemView {{
    background-color: {theme.get('black', '#1E1E1E')};
    color: {fg};
    selection-background-color: {selection};
    border: 1px solid {border};
}}

/* List Widget */
QListWidget {{
    background-color: {theme.get('black', '#1E1E1E')};
    color: {fg};
    border: 2px dashed {accent};
    border-radius: 5px;
    padding: 5px;
}}

QListWidget::item {{
    padding: 5px;
}}

QListWidget::item:selected {{
    background-color: {selection};
    color: {fg};
}}

QListWidget::item:hover {{
    background-color: {theme.get('brightBlack', '#333333')};
}}

/* Text Edit (Read-only displays) */
QTextEdit {{
    background-color: {theme.get('black', '#1E1E1E')};
    color: {fg};
    border: 1px solid {border};
    border-radius: 3px;
    padding: 5px;
}}

QTextEdit:read-only {{
    background-color: {theme.get('brightBlack', '#2A2A2A')};
}}

/* Scroll Area */
QScrollArea {{
    background-color: {bg};
    border: none;
}}

/* Scroll Bars */
QScrollBar:vertical {{
    background-color: {bg};
    width: 12px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {border};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {accent};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {bg};
    height: 12px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {border};
    border-radius: 6px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {accent};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {border};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {bg};
    color: {fg};
    border-top: 1px solid {border};
}}

/* Menu Bar */
QMenuBar {{
    background-color: {bg};
    color: {fg};
    border-bottom: 1px solid {border};
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 4px 8px;
}}

QMenuBar::item:selected {{
    background-color: {selection};
}}

QMenu {{
    background-color: {theme.get('black', '#1E1E1E')};
    color: {fg};
    border: 1px solid {border};
}}

QMenu::item {{
    padding: 5px 20px;
}}

QMenu::item:selected {{
    background-color: {selection};
}}

/* Progress Bar */
QProgressBar {{
    background-color: {theme.get('black', '#1E1E1E')};
    color: {fg};
    border: 1px solid {border};
    border-radius: 3px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {accent};
    border-radius: 2px;
}}

/* QTabWidget */
QTabWidget::pane {{
    border: 1px solid {border};
    background-color: {bg};
}}

QTabBar::tab {{
    background-color: {theme.get('brightBlack', '#2A2A2A')};
    color: {fg};
    border: 1px solid {border};
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {accent};
    color: {theme.get('white', '#FFFFFF')};
    border-bottom: 2px solid {bright_accent};
}}

QTabBar::tab:hover {{
    background-color: {theme.get('brightBlack', '#3A3A3A')};
}}

QTabBar::tab:selected:hover {{
    background-color: {bright_accent};
}}

/* QToolBar */
QToolBar {{
    background-color: {bg};
    border: 1px solid {border};
    spacing: 3px;
    padding: 3px;
}}

QToolButton {{
    background-color: transparent;
    color: {fg};
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 5px 8px;
}}

QToolButton:hover {{
    background-color: {theme.get('brightBlack', '#2A2A2A')};
    border: 1px solid {border};
}}

QToolButton:pressed {{
    background-color: {accent};
    border: 1px solid {accent};
}}

/* Dialog */
QDialog {{
    background-color: {bg};
    color: {fg};
}}

/* Message Box */
QMessageBox {{
    background-color: {bg};
    color: {fg};
}}
"""

        print(f"Generated stylesheet for theme: {theme_name}")
        return stylesheet.strip()

    def apply_theme(self, app, theme_name: str):
        """
        Apply theme to Qt application.

        Args:
            app: QApplication instance
            theme_name: Name of theme to apply
        """
        stylesheet = self.generate_stylesheet(theme_name)
        if stylesheet:
            app.setStyleSheet(stylesheet)
            print(f"Applied theme: {theme_name}")
        else:
            print(f"Failed to apply theme: {theme_name}")
