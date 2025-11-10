import sys
import os
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Suppress Qt font warnings
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'

# Third-party libraries
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLineEdit, QCheckBox, QPushButton,
    QTextEdit, QLabel, QFileDialog, QMessageBox, QGridLayout,
    QScrollArea, QGroupBox, QComboBox, QSpinBox, QListWidgetItem,
    QToolBar, QStatusBar, QSplitter, QTabWidget, QColorDialog,
    QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QAction
import tomlkit

# Local imports
from theme_manager import ThemeManager

# --- Configuration Constants ---

SCHEMA_URL = 'https://starship.rs/config-schema.json'

# Comprehensive Starship Modules
STARSHIP_MODULES = [
    "aws", "azure", "battery", "buf", "bun", "c", "character", "cmake",
    "cmd_duration", "cobol", "conda", "container", "crystal", "daml",
    "dart", "deno", "directory", "direnv", "docker_context", "dotnet",
    "elixir", "elm", "env_var", "erlang", "fennel", "fill", "fossil_branch",
    "fossil_metrics", "gcloud", "git_branch", "git_commit", "git_metrics",
    "git_state", "git_status", "golang", "gradle", "guix_shell", "haskell",
    "haxe", "helm", "hostname", "java", "jobs", "julia", "kotlin", "kubernetes",
    "line_break", "localip", "lua", "memory_usage", "meson", "nats", "nim",
    "nix_shell", "nodejs", "ocaml", "opa", "openstack", "os", "package",
    "perl", "php", "pijul_channel", "pulumi", "purescript", "python", "raku",
    "red", "rlang", "ruby", "rust", "scala", "shell", "shlvl", "singularity",
    "solidity", "spack", "status", "sudo", "swift", "terraform", "time",
    "typst", "username", "vagrant", "vcsh", "vlang", "zig"
]

# Popular/Common modules to show first
COMMON_MODULES = [
    "character", "directory", "git_branch", "git_status", "git_commit",
    "python", "nodejs", "rust", "golang", "java", "docker_context",
    "kubernetes", "aws", "gcloud", "time", "cmd_duration", "status",
    "battery", "memory_usage"
]


def detect_starship_config_path() -> Path:
    """Detect the Starship config path based on the operating system."""
    # Check environment variable first
    if 'STARSHIP_CONFIG' in os.environ:
        return Path(os.environ['STARSHIP_CONFIG'])

    # Platform-specific defaults
    if sys.platform == 'win32':
        # Windows: try multiple locations
        candidates = [
            Path.home() / '.config' / 'starship.toml',
            Path(os.environ.get('APPDATA', '')) / 'starship' / 'starship.toml',
            Path.home() / 'starship.toml',
        ]
    else:
        # Unix-like systems
        candidates = [
            Path.home() / '.config' / 'starship.toml',
            Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'starship.toml',
        ]

    # Return first existing path, or default to ~/.config/starship.toml
    for path in candidates:
        if path and path.exists():
            return path

    return Path.home() / '.config' / 'starship.toml'


# --- Schema Fetcher Thread ---

class SchemaFetcher(QThread):
    """Background thread to fetch Starship schema without blocking UI."""
    schema_loaded = pyqtSignal(dict)
    schema_failed = pyqtSignal(str)

    def run(self):
        try:
            import urllib.request
            with urllib.request.urlopen(SCHEMA_URL, timeout=10) as response:
                schema = json.loads(response.read().decode())
                self.schema_loaded.emit(schema)
        except Exception as e:
            self.schema_failed.emit(str(e))


# --- Main Application Window ---

class StarshipConfigurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Starship Configurator")
        self.setGeometry(100, 100, 1400, 900)

        # Configuration storage
        self.config_path = detect_starship_config_path()
        self.config_data = None
        self.schema_data = None
        self.module_widgets = {}  # Store widget references by module

        # App preferences file
        self.prefs_path = Path.home() / '.config' / 'starship-configurator' / 'preferences.json'

        # Theme manager
        self.theme_manager = ThemeManager(themes_file="themes.json")

        # Build UI first
        self._build_ui()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()

        # Load preferences and apply saved settings
        prefs = self._load_preferences()
        saved_theme = prefs.get('theme', 'Atom')
        saved_widget_font = prefs.get('widget_font_family', 'Sans Serif')
        saved_widget_font_size = prefs.get('widget_font_size', 9)
        saved_code_font = prefs.get('code_font_family', 'Monospace')
        saved_code_font_size = prefs.get('code_font_size', 10)

        # Set UI values to saved preferences (block signals to avoid duplicate saves)
        self.theme_combo.blockSignals(True)
        self.widget_font_combo.blockSignals(True)
        self.widget_font_size_spin.blockSignals(True)
        self.code_font_combo.blockSignals(True)
        self.code_font_size_spin.blockSignals(True)

        self.theme_combo.setCurrentText(saved_theme)
        self.widget_font_combo.setCurrentText(saved_widget_font)
        self.widget_font_size_spin.setValue(saved_widget_font_size)
        self.code_font_combo.setCurrentText(saved_code_font)
        self.code_font_size_spin.setValue(saved_code_font_size)

        self.theme_combo.blockSignals(False)
        self.widget_font_combo.blockSignals(False)
        self.widget_font_size_spin.blockSignals(False)
        self.code_font_combo.blockSignals(False)
        self.code_font_size_spin.blockSignals(False)

        # Apply theme first, then override with custom fonts
        self._apply_selected_theme(saved_theme)
        self._update_widget_fonts()

        # Load config after UI is ready
        self._load_initial_config()

        # Start schema fetch in background
        self.schema_thread = SchemaFetcher()
        self.schema_thread.schema_loaded.connect(self._on_schema_loaded)
        self.schema_thread.schema_failed.connect(self._on_schema_failed)
        self.schema_thread.start()

    def _build_ui(self):
        """Sets up the main layout with tabbed interface."""
        # Central widget with tab layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create main tab widget
        self.main_tabs = QTabWidget()
        main_layout.addWidget(self.main_tabs)

        # === TAB 1: Modules ===
        modules_tab = self._create_modules_tab()
        self.main_tabs.addTab(modules_tab, "🔧 Modules")

        # === TAB 2: Global Settings ===
        global_tab = self._create_global_settings_tab()
        self.main_tabs.addTab(global_tab, "⚙️ Global Settings")

        # === TAB 3: Preview ===
        preview_tab = self._create_preview_tab()
        self.main_tabs.addTab(preview_tab, "✨ Preview")

        # === TAB 4: TOML Editor ===
        toml_tab = self._create_toml_editor_tab()
        self.main_tabs.addTab(toml_tab, "📝 TOML Editor")

    def _create_modules_tab(self) -> QWidget:
        """Create the modules tab with list and config panels."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: Module list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # Search box
        search_label = QLabel("🔍 Search Modules:")
        search_label.setStyleSheet("font-weight: bold; padding: 5px;")
        left_layout.addWidget(search_label)

        self.module_search = QLineEdit()
        self.module_search.setPlaceholderText("Type to filter...")
        self.module_search.textChanged.connect(self._filter_modules)
        left_layout.addWidget(self.module_search)

        # Module category filter
        category_label = QLabel("📦 Filter:")
        category_label.setStyleSheet("font-weight: bold; padding: 5px; margin-top: 10px;")
        left_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["All Modules", "Active Modules", "Inactive Modules"])
        self.category_combo.currentTextChanged.connect(self._update_module_list)
        left_layout.addWidget(self.category_combo)

        # Module list
        self.module_list = QListWidget()
        self.module_list.setAlternatingRowColors(True)
        left_layout.addWidget(self.module_list)

        splitter.addWidget(left_panel)

        # RIGHT: Module config panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        self.stacked_widget = QStackedWidget()
        right_layout.addWidget(self.stacked_widget)

        # Welcome panel (shows when no module selected)
        welcome = QWidget()
        welcome_layout = QVBoxLayout(welcome)
        welcome_label = QLabel("👈 Select a module from the list to configure it")
        welcome_label.setStyleSheet("font-size: 14px; padding: 20px; color: #666;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(welcome_label)
        self.stacked_widget.addWidget(welcome)

        splitter.addWidget(right_panel)

        # Set splitter sizes
        splitter.setSizes([350, 1050])

        layout.addWidget(splitter)
        return tab

    def _create_global_settings_tab(self) -> QWidget:
        """Create comprehensive global settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === General Settings ===
        general_group = QGroupBox("General Settings")
        general_layout = QGridLayout()
        row = 0

        general_layout.addWidget(QLabel("Config Path:"), row, 0)
        path_label = QLabel(str(self.config_path))
        path_label.setStyleSheet("color: #0078d4; padding: 5px;")
        path_label.setWordWrap(True)
        general_layout.addWidget(path_label, row, 1)
        row += 1

        self.add_newline_check = QCheckBox("Add newline before prompt")
        self.add_newline_check.setChecked(True)
        general_layout.addWidget(self.add_newline_check, row, 0, 1, 2)
        row += 1

        general_group.setLayout(general_layout)
        panel_layout.addWidget(general_group)

        # === UI Settings ===
        ui_group = QGroupBox("User Interface Settings")
        ui_layout = QGridLayout()
        row = 0

        ui_layout.addWidget(QLabel("Theme:"), row, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.get_theme_names())
        self.theme_combo.setCurrentText("Atom")  # Default theme
        self.theme_combo.currentTextChanged.connect(self._apply_selected_theme)
        self.theme_combo.setToolTip("Select color theme for the application")
        ui_layout.addWidget(self.theme_combo, row, 1)
        row += 1

        ui_layout.addWidget(QLabel("Widget Font Family:"), row, 0)
        self.widget_font_combo = QComboBox()
        self.widget_font_combo.addItems(["Sans Serif", "Arial", "Helvetica", "Verdana", "Tahoma", "Calibri", "Segoe UI"])
        self.widget_font_combo.setCurrentText("Sans Serif")
        self.widget_font_combo.currentTextChanged.connect(self._update_widget_fonts)
        self.widget_font_combo.setToolTip("Font family for labels, buttons, inputs")
        ui_layout.addWidget(self.widget_font_combo, row, 1)
        row += 1

        ui_layout.addWidget(QLabel("Widget Font Size (pt):"), row, 0)
        self.widget_font_size_spin = QSpinBox()
        self.widget_font_size_spin.setRange(6, 24)
        self.widget_font_size_spin.setValue(9)
        self.widget_font_size_spin.setToolTip("Font size for labels, buttons, inputs")
        self.widget_font_size_spin.valueChanged.connect(self._update_widget_fonts)
        ui_layout.addWidget(self.widget_font_size_spin, row, 1)
        row += 1

        ui_layout.addWidget(QLabel("Code Font Family:"), row, 0)
        self.code_font_combo = QComboBox()
        self.code_font_combo.addItems(["Monospace", "Courier New", "Consolas", "Monaco", "DejaVu Sans Mono", "Fira Code"])
        self.code_font_combo.setCurrentText("Monospace")
        self.code_font_combo.currentTextChanged.connect(self._update_widget_fonts)
        self.code_font_combo.setToolTip("Font family for TOML editor and code displays")
        ui_layout.addWidget(self.code_font_combo, row, 1)
        row += 1

        ui_layout.addWidget(QLabel("Code Font Size (pt):"), row, 0)
        self.code_font_size_spin = QSpinBox()
        self.code_font_size_spin.setRange(6, 24)
        self.code_font_size_spin.setValue(10)
        self.code_font_size_spin.setToolTip("Font size for TOML editor and code displays")
        self.code_font_size_spin.valueChanged.connect(self._update_widget_fonts)
        ui_layout.addWidget(self.code_font_size_spin, row, 1)
        row += 1

        ui_group.setLayout(ui_layout)
        panel_layout.addWidget(ui_group)

        # === Performance Settings ===
        perf_group = QGroupBox("Performance Settings")
        perf_layout = QGridLayout()
        row = 0

        perf_layout.addWidget(QLabel("Scan timeout (ms):"), row, 0)
        self.scan_timeout_spin = QSpinBox()
        self.scan_timeout_spin.setRange(0, 10000)
        self.scan_timeout_spin.setValue(30)
        self.scan_timeout_spin.setToolTip("Timeout for scanning files")
        perf_layout.addWidget(self.scan_timeout_spin, row, 1)
        row += 1

        perf_layout.addWidget(QLabel("Command timeout (ms):"), row, 0)
        self.command_timeout_spin = QSpinBox()
        self.command_timeout_spin.setRange(0, 10000)
        self.command_timeout_spin.setValue(500)
        self.command_timeout_spin.setToolTip("Timeout for executing commands")
        perf_layout.addWidget(self.command_timeout_spin, row, 1)
        row += 1

        perf_layout.addWidget(QLabel("Follow symlinks:"), row, 0)
        self.follow_symlinks_check = QCheckBox("Enable")
        self.follow_symlinks_check.setChecked(True)
        perf_layout.addWidget(self.follow_symlinks_check, row, 1)
        row += 1

        perf_group.setLayout(perf_layout)
        panel_layout.addWidget(perf_group)

        scroll.setWidget(panel)
        layout.addWidget(scroll)

        return tab

    def _create_preview_tab(self) -> QWidget:
        """Create the preview tab with large preview area."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title and description
        title = QLabel("✨ Configuration Preview")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        desc = QLabel("Preview how Starship will parse your configuration. Save and restart your terminal to see the actual prompt.")
        desc.setStyleSheet("padding: 5px; color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Large preview area
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Click 'Generate Preview' to see your configuration...")
        self.preview_text.setFont(QFont("Monospace", 10))
        layout.addWidget(self.preview_text)

        # Action buttons
        button_layout = QHBoxLayout()

        self.preview_button = QPushButton("✨ Generate Preview")
        self.preview_button.clicked.connect(self._generate_preview)
        button_layout.addWidget(self.preview_button)

        self.save_button = QPushButton("💾 Save Configuration")
        self.save_button.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        return tab

    def _create_toml_editor_tab(self) -> QWidget:
        """Create the TOML editor tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("📝 Advanced TOML Editor")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        desc = QLabel("⚠️ Direct editing - be careful with syntax! Use this for advanced configurations.")
        desc.setStyleSheet("padding: 5px; color: #ff6b6b;")
        layout.addWidget(desc)

        # TOML editor
        self.full_config_editor = QTextEdit()
        self.full_config_editor.setPlaceholderText("Loading configuration...")
        self.full_config_editor.setFont(QFont("Monospace", 10))
        layout.addWidget(self.full_config_editor)

        # Buttons
        button_layout = QHBoxLayout()

        reload_btn = QPushButton("🔄 Reload from TOML")
        reload_btn.clicked.connect(self._reload_from_toml_editor)
        reload_btn.setToolTip("Parse the TOML and update all UI fields")
        button_layout.addWidget(reload_btn)

        save_btn = QPushButton("💾 Save Configuration")
        save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(save_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        return tab

    def _create_module_panel(self, module_name: str, schema_props: Optional[Dict] = None, description: Optional[str] = None):
        """Create a configuration panel for a specific module."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title
        title = QLabel(f"🔧 {module_name.replace('_', ' ').title()} Module")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Description section - use example as description
        desc_text = description if description else self._get_module_example(module_name).split('\nExample:')[0]
        desc_group = QGroupBox("📖 Description")
        desc_layout = QVBoxLayout()
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("padding: 5px;")
        desc_layout.addWidget(desc_label)
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)

        # Add example/usage information
        example_group = QGroupBox("💡 Example & Usage")
        example_layout = QVBoxLayout()
        example_text = self._get_module_example(module_name)
        example_label = QLabel(example_text)
        example_label.setWordWrap(True)
        example_label.setStyleSheet("padding: 5px; font-family: 'Monospace';")
        example_layout.addWidget(example_label)
        example_group.setLayout(example_layout)
        layout.addWidget(example_group)

        # Enable/Disable
        enable_check = QCheckBox(f"Enable {module_name} module")
        enable_check.setChecked(True)
        enable_check.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(enable_check)

        # Store widgets for this module
        self.module_widgets[module_name] = {'enabled': enable_check, 'fields': {}}

        # Schema-based fields - ALL module properties
        if schema_props:
            print(f"🔍 DEBUG: Adding all settings for '{module_name}' ({len(schema_props)} properties)")
            settings_group = QGroupBox("Module Settings")
            settings_layout = QGridLayout()
            settings_row = 0

            # Add ALL fields from schema
            for prop_name, prop_schema in schema_props.items():
                label = QLabel(f"{prop_name.replace('_', ' ').title()}:")
                settings_layout.addWidget(label, settings_row, 0)

                # Detect field type
                is_symbol_field = 'symbol' in prop_name.lower()
                is_color_field = any(kw in prop_name.lower() for kw in ['color', 'style', 'fg', 'bg'])
                field_type = prop_schema.get('type', 'string')

                # Create appropriate widget based on type and name
                if field_type == 'string' and (is_color_field or is_symbol_field):
                    # Create container with helper buttons
                    field_container = QWidget()
                    field_h_layout = QHBoxLayout(field_container)
                    field_h_layout.setContentsMargins(0, 0, 0, 0)

                    widget = QLineEdit()
                    if 'default' in prop_schema:
                        widget.setText(str(prop_schema['default']))
                    if 'description' in prop_schema:
                        widget.setPlaceholderText(prop_schema['description'][:50] + "...")

                    field_h_layout.addWidget(widget, stretch=3)

                    # Add emoji picker for symbol fields
                    if is_symbol_field:
                        emoji_btn = QPushButton("😀")
                        emoji_btn.setMaximumWidth(40)
                        emoji_btn.setToolTip("Pick emoji")
                        emoji_btn.clicked.connect(lambda checked, w=widget: self._open_emoji_picker(w))
                        field_h_layout.addWidget(emoji_btn)

                    # Add color picker for color/style fields
                    if is_color_field:
                        color_btn = QPushButton("🎨")
                        color_btn.setMaximumWidth(40)
                        color_btn.setToolTip("Pick color")
                        color_btn.clicked.connect(lambda checked, w=widget: self._open_smart_color_picker(w))
                        field_h_layout.addWidget(color_btn)

                    settings_layout.addWidget(field_container, settings_row, 1)
                    self.module_widgets[module_name]['fields'][prop_name] = widget
                else:
                    # Regular widget without helper buttons
                    widget = self._create_widget_for_schema(prop_schema)
                    settings_layout.addWidget(widget, settings_row, 1)
                    self.module_widgets[module_name]['fields'][prop_name] = widget

                settings_row += 1

            print(f"🔍 DEBUG: Added {settings_row} fields for '{module_name}'")
            settings_group.setLayout(settings_layout)
            layout.addWidget(settings_group)
        else:
            print(f"🔍 DEBUG: No schema_props for '{module_name}' - schema may not be loaded")

        # Help text
        help_label = QLabel(f'💡 <a href="https://starship.rs/config/#{module_name}">View {module_name} documentation</a>')
        help_label.setOpenExternalLinks(True)
        help_label.setStyleSheet("padding: 10px; color: #0066cc;")
        layout.addWidget(help_label)

        scroll.setWidget(panel)
        self.stacked_widget.addWidget(scroll)

        return scroll

    def _get_module_example(self, module_name: str) -> str:
        """Get example and usage information for a module."""
        examples = {
            'aws': 'Shows the current AWS region and profile with expiration timer for temporary credentials.\nExample: ☁️ us-east-1 (prod)\nDisplays AWS CLI configuration.',
            'azure': 'Displays the current Azure Subscription based on the active configuration.\nExample: ☁️ my-subscription\nUseful for Azure CLI users.',
            'battery': 'Shows device battery charge level and current charging status.\nExample: 🔋 85% | ⚡ charging\nDisplayed when below threshold.',
            'character': 'Displays a character (usually an arrow) indicating command success or failure.\nExample: ❯ (green) or ❯ (red)\nChanges color based on last command status.',
            'cmd_duration': 'Shows how long the last command took to execute.\nExample: 🕙 2.3s\nDisplayed when execution time exceeds threshold.',
            'container': 'Displays a symbol and container name when inside a container.\nExample: 📦 container\nDetects Docker/LXC/Podman environments.',
            'directory': 'Displays the path to your current directory, truncated to parent folders.\nExample: 📁 ~/projects/app\nCustomizable truncation and formatting.',
            'docker_context': 'Shows the currently active Docker context.\nExample: 🐳 default\nUseful when working with multiple Docker environments.',
            'dotnet': 'Shows the relevant version of the .NET Core SDK for current directory.\nExample: •NET v8.0.100\nDisplayed in .NET projects.',
            'git_branch': 'Shows the active branch of the repository in current directory.\nExample: 🌱 main | ⎇ feature/new-ui\nDisplays current Git branch name.',
            'git_commit': 'Shows the current commit hash and tag (if any) of repository.\nExample: (7f3a2b1) | 🏷️ v1.0.0\nDisplayed in detached HEAD state.',
            'git_state': 'Shows in directories with git operations in progress (rebase, merge, etc).\nExample: (REBASING 2/10)\nIndicates active Git operations.',
            'git_status': 'Shows symbols representing the state of repository in current directory.\nExample: [+3 ~2 -1 ⇡2]\nIndicates added, modified, deleted files and commits ahead.',
            'git_metrics': 'Shows the number of added and deleted lines in current repository.\nExample: +420 -69\nDisplays line changes in Git repo.',
            'golang': 'Shows the currently installed version of Go.\nExample: 🐹 v1.21.5\nDisplayed when go.mod is present.',
            'hostname': 'Shows the system hostname.\nExample: 🌐 mycomputer\nDisplayed in SSH sessions by default.',
            'java': 'Shows the currently installed version of Java.\nExample: ☕ v21.0.1\nDisplayed in Java projects.',
            'jobs': 'Shows the current number of jobs running.\nExample: ✦2\nDisplays background job count.',
            'kubernetes': 'Displays the current Kubernetes context name and namespace.\nExample: ☸ production/default\nUseful for kubectl users.',
            'lua': 'Shows the currently installed version of Lua.\nExample: 🌙 v5.4.4\nDisplayed when .lua files are detected.',
            'memory_usage': 'Displays system memory consumption and available memory.\nExample: 💾 4.2 GB / 16 GB\nShows RAM usage percentage.',
            'nodejs': 'Displays Node.js version for JavaScript/Node projects.\nExample: ⬢ v20.10.0\nShown when package.json is detected.',
            'package': 'Shows the current project version from package metadata files.\nExample: 📦 v1.2.3\nReads from package.json, Cargo.toml, etc.',
            'php': 'Shows the currently installed PHP version.\nExample: 🐘 v8.2.0\nDisplayed in PHP projects.',
            'python': 'Displays Python version and virtual environment status.\nExample: 🐍 v3.11.2 (.venv)\nShown when in a Python project.',
            'ruby': 'Shows Ruby version for Ruby projects.\nExample: 💎 v3.2.0\nDisplayed when Gemfile is detected.',
            'rust': 'Displays Rust toolchain version and project information.\nExample: 🦀 v1.75.0\nShown in Rust projects with Cargo.toml.',
            'scala': 'Shows Scala version for JVM-based functional programming.\nExample: 🆂 v3.3.1\nDisplayed when .scala files or build.sbt are detected.',
            'shell': 'Displays the current shell name and version.\nExample: 🐚 bash\nShows active shell indicator.',
            'status': 'Displays the exit status code of the last executed command.\nExample: ✘ 127\nOnly shown when command fails.',
            'sudo': 'Shows a symbol when sudo credentials are cached.\nExample: 🧙 \nIndicates active sudo session.',
            'terraform': 'Shows Terraform workspace and version for infrastructure automation.\nExample: 💠 workspace: default\nUseful for Terraform users.',
            'time': 'Displays the current time in a customizable format.\nExample: 🕙 15:45:32\nShows current system time.',
            'username': 'Displays the current user account name.\nExample: rafal@hostname\nShown by default for root user.',
        }

        return examples.get(module_name,
            f"Configures the '{module_name}' module for your Starship prompt.\n"
            f"See full documentation: https://starship.rs/config/#{module_name}"
        )

    def _open_smart_color_picker(self, target_line_edit: QLineEdit):
        """Smart color picker that handles multiple color formats."""
        import re

        color = QColorDialog.getColor()
        if not color.isValid():
            return

        color_hex = color.name()  # Returns hex like #ff0000
        current_text = target_line_edit.text().strip()

        # Pattern 1: Starship format string [text](style) - extract style and replace color
        starship_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        if re.search(starship_pattern, current_text):
            def replace_color_in_style(match):
                text = match.group(1)
                style = match.group(2)
                # Replace hex color if exists, otherwise append
                if re.search(r'#[0-9a-fA-F]{6}', style):
                    new_style = re.sub(r'#[0-9a-fA-F]{6}', color_hex, style, count=1)
                elif re.search(r'\b(red|green|blue|yellow|purple|cyan|white|black)\b', style):
                    # Replace named color
                    new_style = re.sub(r'\b(red|green|blue|yellow|purple|cyan|white|black)\b', color_hex, style, count=1)
                else:
                    new_style = f"{style} {color_hex}"
                return f"[{text}]({new_style})"

            new_text = re.sub(starship_pattern, replace_color_in_style, current_text, count=1)
            target_line_edit.setText(new_text)
            return

        # Pattern 2: Multiple color specs (bg: fg:) - replace first hex or append
        if re.search(r'\b(bg|fg|color):', current_text):
            # Try to replace existing hex after bg:, fg:, or color:
            if re.search(r'(bg|fg|color):#[0-9a-fA-F]{6}', current_text):
                new_text = re.sub(r'(bg|fg|color):#[0-9a-fA-F]{6}', rf'\1:{color_hex}', current_text, count=1)
                target_line_edit.setText(new_text)
            else:
                # Append new color spec
                target_line_edit.setText(f"{current_text} fg:{color_hex}")
            return

        # Pattern 3: Simple hex replacement
        hex_pattern = r'#[0-9a-fA-F]{6}\b'
        if re.search(hex_pattern, current_text):
            new_text = re.sub(hex_pattern, color_hex, current_text, count=1)
            target_line_edit.setText(new_text)
            return

        # Pattern 4: Named colors (red, green, etc.)
        named_color_pattern = r'\b(red|green|blue|yellow|purple|cyan|white|black)\b'
        if re.search(named_color_pattern, current_text):
            new_text = re.sub(named_color_pattern, color_hex, current_text, count=1)
            target_line_edit.setText(new_text)
            return

        # Pattern 5: No color found - append
        if current_text:
            target_line_edit.setText(f"{current_text} {color_hex}")
        else:
            target_line_edit.setText(color_hex)

    def _open_emoji_picker(self, target_line_edit: QLineEdit):
        """Opens an emoji picker dialog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QPushButton, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Pick Emoji")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Common emojis for Starship
        starship_emojis = [
            # General
            "🚀", "✨", "⚡", "🔥", "💎", "🌟", "⭐", "✅", "❌", "⚠️",
            # Arrows & symbols
            "❯", "❮", "►", "◄", "→", "←", "↑", "↓", "»", "«",
            # Programming
            "🐍", "🦀", "🐹", "☕", "📦", "🔧", "⚙️", "🛠️", "💻", "📝",
            # Git & Version Control
            "🌱", "🌿", "🔀", "📊", "🏷️", "🔖", "📌", "🔍",
            # Cloud & Infrastructure
            "☁️", "🐳", "☸️", "🌐", "🖥️", "💾", "🗄️",
            # Battery & Status
            "🔋", "⚡", "💀", "󰁽", "󰂎", "󰁹", "󰁾", "󰂀", "󰂂", "󰁺",
            # Time & Misc
            "🕙", "⏱️", "⏰", "🔔", "🧙", "👤", "🏠", "📁", "📂"
        ]

        # Create grid of emoji buttons
        grid = QGridLayout()
        row, col = 0, 0
        for emoji in starship_emojis:
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("font-size: 20px;")
            btn.clicked.connect(lambda checked, e=emoji, d=dialog: self._insert_emoji(target_line_edit, e, d))
            grid.addWidget(btn, row, col)
            col += 1
            if col >= 10:
                col = 0
                row += 1

        layout.addLayout(grid)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def _insert_emoji(self, target_line_edit: QLineEdit, emoji: str, dialog: QDialog):
        """Insert selected emoji into the field."""
        current_text = target_line_edit.text()
        # Replace first emoji or append
        import re
        # Common emoji pattern (basic support)
        emoji_pattern = r'[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]+'
        if re.search(emoji_pattern, current_text):
            new_text = re.sub(emoji_pattern, emoji, current_text, count=1)
            target_line_edit.setText(new_text)
        else:
            target_line_edit.setText(emoji if not current_text else f"{emoji} {current_text}")
        dialog.accept()

    def _create_widget_for_schema(self, prop_schema: Dict) -> QWidget:
        """Create appropriate widget based on JSON schema property type."""
        prop_type = prop_schema.get('type', 'string')

        if prop_type == 'boolean':
            widget = QCheckBox()
            if 'default' in prop_schema:
                widget.setChecked(prop_schema['default'])
            return widget
        elif prop_type == 'integer':
            widget = QSpinBox()
            # QSpinBox uses 32-bit signed integers
            SPINBOX_MIN = -2147483648
            SPINBOX_MAX = 2147483647

            # Clamp schema min/max to QSpinBox limits
            schema_min = max(prop_schema.get('minimum', 0), SPINBOX_MIN)
            schema_max = min(prop_schema.get('maximum', 999999), SPINBOX_MAX)

            widget.setRange(schema_min, schema_max)

            if 'default' in prop_schema:
                default_val = prop_schema['default']
                # Clamp default to widget range
                clamped_default = max(schema_min, min(default_val, schema_max))
                widget.setValue(clamped_default)
                if clamped_default != default_val:
                    print(f"🔍 DEBUG: Clamped default {default_val} to {clamped_default}")
            return widget
        elif prop_type == 'array':
            widget = QTextEdit()
            widget.setMaximumHeight(60)
            widget.setPlaceholderText("Enter values, one per line...")
            return widget
        else:  # string or unknown
            widget = QLineEdit()
            if 'default' in prop_schema:
                widget.setText(str(prop_schema['default']))
            if 'description' in prop_schema:
                widget.setPlaceholderText(prop_schema['description'][:50] + "...")
            return widget

    def _create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        load_action = QAction("📂 Load Configuration...", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self._load_config_from_file)
        file_menu.addAction(load_action)

        save_action = QAction("💾 Save Configuration", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("❌ Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        reload_action = QAction("🔄 Reload from Disk", self)
        reload_action.setShortcut("F5")
        reload_action.triggered.connect(self._reload_config)
        edit_menu.addAction(reload_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        docs_action = QAction("📚 Starship Documentation", self)
        docs_action.triggered.connect(lambda: self._open_url("https://starship.rs/config/"))
        help_menu.addAction(docs_action)

        about_action = QAction("ℹ️ About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """Create application toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Quick actions
        toolbar.addAction("💾 Save", self._save_config)
        toolbar.addAction("📂 Load", self._load_config_from_file)
        toolbar.addSeparator()
        toolbar.addAction("🔄 Reload", self._reload_config)

    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"Ready - Config: {self.config_path}")


    # === Configuration Management ===

    def _load_initial_config(self):
        """Load the starship.toml file or create a default structure."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = tomlkit.load(f)
                self.status_bar.showMessage(f"✅ Loaded: {self.config_path}", 5000)
                self._populate_ui_from_config()
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Could not load config:\n{e}")
                self.config_data = self._create_default_config()
        else:
            response = QMessageBox.question(
                self,
                "No Config Found",
                f"No Starship configuration found at:\n{self.config_path}\n\nCreate a new one?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if response == QMessageBox.StandardButton.Yes:
                self.config_data = self._create_default_config()
            else:
                self.config_data = tomlkit.document()

        self._update_full_editor()
        self._update_module_list()

    def _create_default_config(self) -> tomlkit.TOMLDocument:
        """Create a basic default configuration."""
        doc = tomlkit.document()
        doc.add(tomlkit.comment("Starship Configuration"))
        doc.add(tomlkit.comment(f"Generated by Starship Configurator"))
        doc.add(tomlkit.nl())

        doc['add_newline'] = True
        doc['scan_timeout'] = 30
        doc['command_timeout'] = 500

        # Add a basic character module
        char_table = tomlkit.table()
        char_table['success_symbol'] = "[❯](bold green)"
        char_table['error_symbol'] = "[❯](bold red)"
        doc['character'] = char_table

        return doc

    def _populate_ui_from_config(self):
        """Populate UI widgets from loaded configuration."""
        if not self.config_data:
            return

        # Global settings
        self.add_newline_check.setChecked(self.config_data.get('add_newline', True))
        self.scan_timeout_spin.setValue(self.config_data.get('scan_timeout', 30))
        self.command_timeout_spin.setValue(self.config_data.get('command_timeout', 500))
        self.follow_symlinks_check.setChecked(self.config_data.get('follow_symlinks', True))

        # Module settings will be loaded when panels are created
        self._update_full_editor()

    def _update_full_editor(self):
        """Update the full TOML editor with current config."""
        if self.config_data:
            self.full_config_editor.setPlainText(self.config_data.as_string())

    def _update_module_list(self):
        """Update the module list based on category and search."""
        # Disconnect signals temporarily to prevent multiple triggers
        try:
            self.module_list.currentRowChanged.disconnect()
            self.module_list.itemChanged.disconnect()
        except:
            pass

        self.module_list.clear()

        # Determine which modules to show
        category = self.category_combo.currentText()
        search_text = self.module_search.text().lower()

        if category == "Active Modules":
            modules = [m for m in STARSHIP_MODULES if m in self.config_data and not self.config_data[m].get('disabled', False)] if self.config_data else []
        elif category == "Inactive Modules":
            modules = [m for m in STARSHIP_MODULES if m not in self.config_data or self.config_data[m].get('disabled', False)] if self.config_data else STARSHIP_MODULES
        else:  # All Modules
            modules = sorted(STARSHIP_MODULES)

        # Filter by search
        if search_text:
            modules = [m for m in modules if search_text in m.lower()]

        # Add modules to list with checkboxes
        for module in modules:
            # Check if module is enabled in config
            is_enabled = False
            if self.config_data and module in self.config_data:
                module_config = self.config_data[module]
                # Module is enabled if it exists and disabled is not True
                is_enabled = not module_config.get('disabled', False)

            item = QListWidgetItem(f"  {module}")
            item.setData(Qt.ItemDataRole.UserRole, module)

            # Make item checkable
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if is_enabled else Qt.CheckState.Unchecked)

            self.module_list.addItem(item)

        # Reconnect signals
        self.module_list.currentRowChanged.connect(self._on_module_selected)
        self.module_list.itemChanged.connect(self._on_module_checkbox_changed)

    def _filter_modules(self, text: str):
        """Filter module list based on search text."""
        self._update_module_list()

    def _on_module_checkbox_changed(self, item: QListWidgetItem):
        """Handle module checkbox toggle."""
        module_name = item.data(Qt.ItemDataRole.UserRole)
        if not module_name:
            return  # Skip global settings

        is_checked = item.checkState() == Qt.CheckState.Checked

        # Ensure config_data exists
        if not self.config_data:
            self.config_data = self._create_default_config()

        # Create module table if it doesn't exist
        if module_name not in self.config_data:
            self.config_data[module_name] = tomlkit.table()

        # Update the disabled field
        if is_checked:
            # Module is enabled, remove 'disabled' field if it exists
            if 'disabled' in self.config_data[module_name]:
                del self.config_data[module_name]['disabled']
        else:
            # Module is disabled, set 'disabled' to true
            self.config_data[module_name]['disabled'] = True

        # Update the TOML editor
        self._update_full_editor()

        # Update status bar
        status = "enabled" if is_checked else "disabled"
        self.status_bar.showMessage(f"Module '{module_name}' {status}", 2000)

    def _on_module_selected(self, row: int):
        """Handle module selection from list."""
        item = self.module_list.item(row)
        if item:
            module_name = item.data(Qt.ItemDataRole.UserRole)
            if module_name:
                self._show_module_panel(module_name)

    def _show_module_panel(self, module_name: str):
        """Show or create panel for the given module."""
        # Check if panel already exists
        if module_name not in self.module_widgets:
            # Get schema for this module if available
            schema_props = None
            schema_description = None
            print(f"🔍 DEBUG: Creating panel for '{module_name}'")
            print(f"🔍 DEBUG: schema_data available: {self.schema_data is not None}")
            if self.schema_data and 'properties' in self.schema_data:
                module_schema = self.schema_data['properties'].get(module_name, {})
                print(f"🔍 DEBUG: module_schema keys: {list(module_schema.keys())}")

                # Resolve $ref if present (Starship schema uses $ref to $defs)
                if '$ref' in module_schema:
                    ref_path = module_schema['$ref']
                    print(f"🔍 DEBUG: Resolving $ref: {ref_path}")
                    # Extract definition name from "#/$defs/DirectoryConfig" format
                    if ref_path.startswith('#/$defs/'):
                        def_name = ref_path.replace('#/$defs/', '')
                        if '$defs' in self.schema_data and def_name in self.schema_data['$defs']:
                            resolved_schema = self.schema_data['$defs'][def_name]
                            schema_props = resolved_schema.get('properties', {})
                            schema_description = resolved_schema.get('description', None)
                            print(f"🔍 DEBUG: Resolved to {def_name}, found {len(schema_props)} properties")
                        else:
                            print(f"🔍 DEBUG: Could not resolve $ref: {ref_path}")
                elif 'allOf' in module_schema:
                    print(f"🔍 DEBUG: '{module_name}' uses allOf pattern, extracting properties...")
                    for item in module_schema['allOf']:
                        if 'properties' in item:
                            schema_props = item['properties']
                            print(f"🔍 DEBUG: Found properties in allOf: {list(schema_props.keys())[:5]}")
                            break
                else:
                    schema_props = module_schema.get('properties', {})
                    schema_description = module_schema.get('description', None)

                print(f"🔍 DEBUG: Found {len(schema_props) if schema_props else 0} schema properties for '{module_name}'")
            else:
                print(f"🔍 DEBUG: No schema data available yet for '{module_name}'")

            panel = self._create_module_panel(module_name, schema_props, schema_description)

            # Store the panel index
            panel_index = self.stacked_widget.count() - 1  # Index of the panel we just added
            self.module_widgets[module_name]['panel_index'] = panel_index

            # Load existing config for this module
            if self.config_data and module_name in self.config_data:
                self._load_module_config(module_name)

        # Show the panel
        if module_name in self.module_widgets and 'panel_index' in self.module_widgets[module_name]:
            self.stacked_widget.setCurrentIndex(self.module_widgets[module_name]['panel_index'])

    def _load_module_config(self, module_name: str):
        """Load configuration values for a specific module into its widgets."""
        if not self.config_data or module_name not in self.config_data:
            return

        module_config = self.config_data[module_name]
        widgets = self.module_widgets.get(module_name, {})

        if 'fields' in widgets:
            for field_name, widget in widgets['fields'].items():
                if field_name in module_config:
                    value = module_config[field_name]

                    if isinstance(widget, QCheckBox):
                        widget.setChecked(bool(value))
                    elif isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QSpinBox):
                        widget.setValue(int(value))
                    elif isinstance(widget, QTextEdit):
                        if isinstance(value, list):
                            widget.setPlainText('\n'.join(str(v) for v in value))
                        else:
                            widget.setPlainText(str(value))

    def _update_config_from_gui(self):
        """Update config_data from all GUI widgets."""
        # Global settings
        self.config_data['add_newline'] = self.add_newline_check.isChecked()
        self.config_data['scan_timeout'] = self.scan_timeout_spin.value()
        self.config_data['command_timeout'] = self.command_timeout_spin.value()
        self.config_data['follow_symlinks'] = self.follow_symlinks_check.isChecked()

        # Module settings
        for module_name, widget_dict in self.module_widgets.items():
            if not widget_dict.get('enabled', QCheckBox()).isChecked():
                # Module is disabled, skip or mark as disabled
                if module_name in self.config_data:
                    self.config_data[module_name]['disabled'] = True
                continue

            # Create module table if not exists
            if module_name not in self.config_data:
                self.config_data[module_name] = tomlkit.table()

            module_table = self.config_data[module_name]

            # Update fields
            for field_name, widget in widget_dict.get('fields', {}).items():
                value = None

                if isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                    if not value and field_name != 'disabled':
                        continue  # Don't save unchecked non-disabled checkboxes
                elif isinstance(widget, QLineEdit):
                    value = widget.text().strip()
                elif isinstance(widget, QSpinBox):
                    value = widget.value()
                elif isinstance(widget, QTextEdit):
                    text = widget.toPlainText().strip()
                    if text:
                        value = text.split('\n')

                if value:
                    module_table[field_name] = value
                elif field_name in module_table:
                    del module_table[field_name]

        self._update_full_editor()

    # === Actions ===

    def _save_config(self):
        """Save configuration to starship.toml."""
        try:
            self._update_config_from_gui()

            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(self.config_data.as_string())

            QMessageBox.information(
                self,
                "✅ Save Successful",
                f"Configuration saved to:\n{self.config_path}\n\n"
                "Restart your terminal to see changes!"
            )
            self.status_bar.showMessage(f"✅ Saved: {self.config_path}", 5000)

        except Exception as e:
            QMessageBox.critical(self, "❌ Save Error", f"Failed to save:\n{e}")

    def _export_config(self):
        """Export configuration to a custom file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Configuration",
            str(Path.home() / "starship.toml"),
            "TOML Files (*.toml);;All Files (*)"
        )

        if file_path:
            try:
                self._update_config_from_gui()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.config_data.as_string())
                QMessageBox.information(self, "✅ Export Successful", f"Exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "❌ Export Error", f"Failed to export:\n{e}")

    def _load_config_from_file(self):
        """Load configuration from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            str(self.config_path.parent),
            "TOML Files (*.toml);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.config_data = tomlkit.load(f)

                self._populate_ui_from_config()
                self._update_module_list()

                QMessageBox.information(self, "✅ Load Successful", f"Loaded from:\n{file_path}")
                self.status_bar.showMessage(f"✅ Loaded: {file_path}", 5000)

            except Exception as e:
                QMessageBox.critical(self, "❌ Load Error", f"Failed to load:\n{e}")

    def _reload_config(self):
        """Reload configuration from disk."""
        self._load_initial_config()
        QMessageBox.information(self, "🔄 Reloaded", "Configuration reloaded from disk.")

    def _reload_from_toml_editor(self):
        """Reload config from the TOML editor text."""
        try:
            toml_text = self.full_config_editor.toPlainText()
            self.config_data = tomlkit.loads(toml_text)
            self._populate_ui_from_config()
            self._update_module_list()
            QMessageBox.information(self, "✅ Reloaded", "Configuration reloaded from TOML editor.")
        except Exception as e:
            QMessageBox.critical(self, "❌ Parse Error", f"Invalid TOML:\n{e}")

    def _generate_preview(self):
        """Generate preview by showing the current configuration."""
        try:
            self._update_config_from_gui()

            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False, encoding='utf-8') as f:
                temp_path = f.name
                f.write(self.config_data.as_string())

            try:
                # Use starship print-config to show the parsed configuration
                # Set STARSHIP_CONFIG environment variable
                env = os.environ.copy()
                env['STARSHIP_CONFIG'] = temp_path

                result = subprocess.run(
                    ['starship', 'print-config'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding='utf-8',
                    env=env
                )

                if result.returncode == 0:
                    # Show the parsed config
                    preview_text = "📋 Configuration Preview (as parsed by Starship):\n"
                    preview_text += "=" * 60 + "\n\n"
                    preview_text += result.stdout.strip()
                    preview_text += "\n\n" + "=" * 60
                    preview_text += "\n💡 Save your config and restart your terminal to see the actual prompt."

                    self.preview_text.setPlainText(preview_text)
                    self.status_bar.showMessage("✨ Config preview generated", 3000)
                else:
                    # Fallback: just show the raw TOML
                    preview_text = "📋 Your Configuration:\n"
                    preview_text += "=" * 60 + "\n\n"
                    preview_text += self.config_data.as_string()
                    preview_text += "\n\n" + "=" * 60
                    preview_text += "\n💡 Save and restart your terminal to see changes."

                    self.preview_text.setPlainText(preview_text)
                    self.status_bar.showMessage("⚠️ Showing raw config (starship command issue)", 3000)

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass

        except FileNotFoundError:
            # If starship isn't installed, just show the config
            preview_text = "📋 Your Configuration:\n"
            preview_text += "=" * 60 + "\n\n"
            preview_text += self.config_data.as_string()
            preview_text += "\n\n" + "=" * 60
            preview_text += "\n\n⚠️ 'starship' command not found.\n"
            preview_text += "Install Starship to validate your config:\n"
            preview_text += "https://starship.rs/guide/#-installation"

            self.preview_text.setPlainText(preview_text)
            self.status_bar.showMessage("⚠️ Starship not installed - showing raw config", 3000)

        except subprocess.TimeoutExpired:
            self.preview_text.setPlainText("❌ Preview timed out")
        except Exception as e:
            self.preview_text.setPlainText(f"❌ Error: {e}")

    # === Schema Handling ===

    def _on_schema_loaded(self, schema: Dict):
        """Handle successful schema loading."""
        self.schema_data = schema
        print("🔍 DEBUG: Schema loaded successfully!")
        print(f"🔍 DEBUG: Schema has {len(schema.get('properties', {}))} module definitions")

        # Debug: Show schema structure for 'directory' module
        if 'properties' in schema and 'directory' in schema['properties']:
            dir_schema = schema['properties']['directory']
            print(f"🔍 DEBUG: Schema structure for 'directory': {list(dir_schema.keys())}")
            if 'allOf' in dir_schema:
                print(f"🔍 DEBUG: 'directory' uses 'allOf' pattern")
            if 'properties' in dir_schema:
                print(f"🔍 DEBUG: 'directory' has direct properties: {list(dir_schema['properties'].keys())[:5]}")

        self.status_bar.showMessage("✅ Schema loaded - enhanced fields available", 5000)

    def _on_schema_failed(self, error: str):
        """Handle schema loading failure."""
        print(f"🔍 DEBUG: Schema failed to load: {error}")
        self.status_bar.showMessage(f"⚠️ Schema unavailable: {error}", 5000)

    # === Utility Methods ===

    def _update_widget_fonts(self):
        """Update all widget fonts based on current settings."""
        widget_font_family = self.widget_font_combo.currentText()
        widget_font_size = self.widget_font_size_spin.value()
        code_font_family = self.code_font_combo.currentText()
        code_font_size = self.code_font_size_spin.value()

        # Get current theme and override font settings
        current_theme = self.theme_combo.currentText()
        theme = self.theme_manager.get_theme(current_theme)

        if theme:
            # Override font settings in theme
            theme['fontFamily'] = widget_font_family
            theme['fontSize'] = f'{widget_font_size}pt'
            theme['labelFontSize'] = f'{widget_font_size}pt'
            theme['buttonFontSize'] = f'{widget_font_size}pt'
            theme['inputFontSize'] = f'{widget_font_size}pt'
            theme['codeFontFamily'] = code_font_family
            theme['codeFontSize'] = f'{code_font_size}pt'

            # Re-apply theme with updated fonts
            stylesheet = self.theme_manager.generate_stylesheet(current_theme)
            QApplication.instance().setStyleSheet(stylesheet)

        # Save font preferences
        prefs = self._load_preferences()
        prefs['widget_font_family'] = widget_font_family
        prefs['widget_font_size'] = widget_font_size
        prefs['code_font_family'] = code_font_family
        prefs['code_font_size'] = code_font_size
        self._save_preferences(prefs)

        self.status_bar.showMessage(f"Fonts updated: {widget_font_family} {widget_font_size}pt", 2000)

    def _apply_selected_theme(self, theme_name: str):
        """Apply the selected theme from theme manager."""
        self.theme_manager.apply_theme(QApplication.instance(), theme_name)
        self.status_bar.showMessage(f"Applied theme: {theme_name}", 2000)

        # Save theme preference
        prefs = self._load_preferences()
        prefs['theme'] = theme_name
        self._save_preferences(prefs)

    def _load_preferences(self) -> Dict:
        """Load user preferences from JSON file."""
        try:
            if self.prefs_path.exists():
                with open(self.prefs_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load preferences: {e}")
        return {}

    def _save_preferences(self, prefs: Dict):
        """Save user preferences to JSON file."""
        try:
            self.prefs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.prefs_path, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            print(f"Failed to save preferences: {e}")

    def _open_url(self, url: str):
        """Open URL in default browser."""
        import webbrowser
        webbrowser.open(url)

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Starship Configurator",
            "<h2>🚀 Starship Configurator</h2>"
            "<p>A modern GUI for configuring Starship prompt</p>"
            "<p>Version: 2.1</p>"
            "<p>Features: Dark/Light themes, 90+ modules, Schema-driven widgets</p>"
            "<p><a href='https://starship.rs'>Starship Homepage</a></p>"
            "<p><a href='https://github.com'>GitHub Repository</a></p>"
        )


# === Application Entry Point ===

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Starship Configurator")
    app.setOrganizationName("Starship")

    # Set application-wide font
    font = QFont("Sans Serif", 9)
    app.setFont(font)

    window = StarshipConfigurator()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
