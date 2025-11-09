import sys
import os
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Third-party libraries
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLineEdit, QCheckBox, QPushButton,
    QTextEdit, QLabel, QFileDialog, QMessageBox, QGridLayout,
    QScrollArea, QGroupBox, QComboBox, QSpinBox, QListWidgetItem,
    QToolBar, QStatusBar, QSplitter, QTabWidget
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QAction
import tomlkit

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

        # Theme state (default to light)
        self.is_dark_mode = False

        # Build UI first
        self._build_ui()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()
        self._apply_theme()

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

        # === TAB 3: TOML Editor ===
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

        ui_layout.addWidget(QLabel("Interface Font Size:"), row, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(9)
        self.font_size_spin.setToolTip("Adjust the size of text throughout the application")
        self.font_size_spin.valueChanged.connect(self._update_app_font_size)
        ui_layout.addWidget(self.font_size_spin, row, 1)
        row += 1

        ui_layout.addWidget(QLabel("Code Editor Font Size:"), row, 0)
        self.code_font_size_spin = QSpinBox()
        self.code_font_size_spin.setRange(8, 24)
        self.code_font_size_spin.setValue(10)
        self.code_font_size_spin.setToolTip("Adjust the size of monospace text in TOML editor")
        self.code_font_size_spin.valueChanged.connect(self._update_code_font_size)
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

        # === Palette Settings ===
        palette_group = QGroupBox("Color Palette (Optional)")
        palette_layout = QGridLayout()
        palette_layout.addWidget(QLabel("Override terminal colors with custom palette"))
        palette_group.setLayout(palette_layout)
        panel_layout.addWidget(palette_group)

        # === Custom Format ===
        format_group = QGroupBox("Custom Prompt Format (Advanced)")
        format_layout = QVBoxLayout()
        format_layout.addWidget(QLabel("Override default module order and format:"))
        self.format_edit = QTextEdit()
        self.format_edit.setPlaceholderText("Leave empty for default format...\nExample: $username$hostname$directory$git_branch$character")
        self.format_edit.setMaximumHeight(100)
        format_layout.addWidget(self.format_edit)
        format_group.setLayout(format_layout)
        panel_layout.addWidget(format_group)

        scroll.setWidget(panel)
        layout.addWidget(scroll)

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

        # Description section (if available from schema)
        if description:
            desc_group = QGroupBox("📖 Description")
            desc_layout = QVBoxLayout()
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("padding: 5px;")
            desc_layout.addWidget(desc_label)
            desc_group.setLayout(desc_layout)
            layout.addWidget(desc_group)
        else:
            # Fallback description if schema doesn't provide one
            desc_group = QGroupBox("📖 About This Module")
            desc_layout = QVBoxLayout()
            desc_label = QLabel(f"The '{module_name}' module displays information in your Starship prompt.")
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

        # Common fields group
        common_group = QGroupBox("Common Settings")
        common_layout = QGridLayout()
        row = 0

        # Format field
        common_layout.addWidget(QLabel("Format:"), row, 0)
        format_input = QLineEdit()
        format_input.setPlaceholderText("Custom format string...")
        common_layout.addWidget(format_input, row, 1)
        self.module_widgets[module_name]['fields']['format'] = format_input
        row += 1

        # Style field
        common_layout.addWidget(QLabel("Style:"), row, 0)
        style_input = QLineEdit()
        style_input.setPlaceholderText("e.g., 'bold red'")
        common_layout.addWidget(style_input, row, 1)
        self.module_widgets[module_name]['fields']['style'] = style_input
        row += 1

        # Disabled field
        common_layout.addWidget(QLabel("Disabled:"), row, 0)
        disabled_check = QCheckBox("Disable this module")
        common_layout.addWidget(disabled_check, row, 1)
        self.module_widgets[module_name]['fields']['disabled'] = disabled_check
        row += 1

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        # Schema-based fields (if schema available)
        if schema_props:
            schema_group = QGroupBox("Module-Specific Settings")
            schema_layout = QGridLayout()
            schema_row = 0

            # Add fields based on schema
            for prop_name, prop_schema in schema_props.items():
                if prop_name in ['format', 'style', 'disabled']:
                    continue  # Already handled above

                label = QLabel(f"{prop_name.replace('_', ' ').title()}:")
                schema_layout.addWidget(label, schema_row, 0)

                # Create appropriate widget based on type
                widget = self._create_widget_for_schema(prop_schema)
                schema_layout.addWidget(widget, schema_row, 1)
                self.module_widgets[module_name]['fields'][prop_name] = widget
                schema_row += 1

                if schema_row > 10:  # Limit fields to avoid overwhelming UI
                    break

            schema_group.setLayout(schema_layout)
            layout.addWidget(schema_group)

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
            'docker_context': 'Shows the active Docker context.\nExample: 🐳 default\nUseful when working with multiple Docker environments.',
            'git_branch': 'Displays the current Git branch.\nExample: 🌱 main | ⎇ feature/new-ui\nShows branch name with custom symbols.',
            'git_status': 'Shows Git repository status (changes, staged files).\nExample: [+3 ~2 -1]\nIndicates added, modified, and deleted files.',
            'python': 'Shows Python version and virtual environment.\nExample: 🐍 v3.11.2 (.venv)\nDisplays when in a Python project.',
            'nodejs': 'Displays Node.js version.\nExample: ⬢ v20.10.0\nShows when package.json is detected.',
            'rust': 'Shows Rust version via rustc.\nExample: 🦀 v1.75.0\nDisplays in Rust projects.',
            'golang': 'Displays Go version.\nExample: 🐹 v1.21.5\nShows when go.mod is present.',
            'java': 'Shows Java version.\nExample: ☕ v21.0.1\nDisplays in Java projects.',
            'kubernetes': 'Shows current Kubernetes context and namespace.\nExample: ☸ production/default\nUseful for kubectl users.',
            'aws': 'Displays active AWS profile and region.\nExample: ☁️ us-east-1 (prod)\nShows AWS CLI configuration.',
            'gcloud': 'Shows Google Cloud project and region.\nExample: ☁️ my-project (us-central1)\nFor GCP users.',
            'directory': 'Shows current working directory path.\nExample: 📁 ~/projects/app\nCustomizable truncation and formatting.',
            'character': 'The prompt character (changes color on error).\nExample: ❯ (green) or ❯ (red)\nIndicates last command success/failure.',
            'cmd_duration': 'Shows how long the last command took.\nExample: 🕙 2.3s\nDisplayed when above threshold.',
            'time': 'Displays current time.\nExample: 🕙 15:45:32\nCustomizable time format.',
            'battery': 'Shows battery level and status.\nExample: 🔋 85%\nDisplayed when below threshold.',
            'memory_usage': 'Shows system memory usage.\nExample: 💾 4.2 GB / 16 GB\nDisplays RAM consumption.',
            'status': 'Shows exit code of last command.\nExample: ✘ 127\nOnly shown on errors.',
            'terraform': 'Shows Terraform workspace and version.\nExample: 💠 workspace: default\nFor Terraform users.',
            'container': 'Indicates if running inside a container.\nExample: 📦 container\nDetects Docker/LXC/Podman.',
        }

        return examples.get(module_name,
            f"Configures the '{module_name}' module.\n"
            f"See documentation: https://starship.rs/config/#{module_name}"
        )

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
            widget.setRange(prop_schema.get('minimum', 0), prop_schema.get('maximum', 999999))
            if 'default' in prop_schema:
                widget.setValue(prop_schema['default'])
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

        # View menu
        view_menu = menubar.addMenu("&View")

        self.theme_action = QAction("🌙 Dark Mode", self)
        self.theme_action.setShortcut("Ctrl+T")
        self.theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.theme_action)

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
        toolbar.addSeparator()

        # Theme toggle button
        self.theme_button = toolbar.addAction("🌙 Dark Mode", self._toggle_theme)

    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"Ready - Config: {self.config_path}")

    def _apply_theme(self):
        """Apply the current theme (light or dark)."""
        if self.is_dark_mode:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def _apply_light_theme(self):
        """Apply light theme stylesheet."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                background-color: #f5f5f5;
                color: #000000;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
                color: #000000;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: #ffffff;
                color: #000000;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
                background-color: white;
                color: #000000;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border: 2px solid #0078d4;
            }
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
                color: #000000;
            }
            QListWidget::item {
                padding: 5px;
                color: #000000;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e5f3ff;
            }
            QCheckBox {
                spacing: 5px;
                color: #000000;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #666666;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 2px solid #0078d4;
            }
            QListWidget::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #666666;
                border-radius: 3px;
                background-color: white;
            }
            QListWidget::indicator:checked {
                background-color: #0078d4;
                border: 2px solid #0078d4;
            }
            QLabel {
                color: #000000;
                background-color: transparent;
            }
            QMenuBar {
                background-color: #ffffff;
                color: #000000;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QToolBar {
                background-color: #ffffff;
                border-bottom: 1px solid #cccccc;
                spacing: 3px;
                padding: 3px;
            }
            QStatusBar {
                background-color: #ffffff;
                color: #000000;
                border-top: 1px solid #cccccc;
            }
            QScrollArea {
                border: none;
                background-color: #f5f5f5;
            }
        """)

    def _apply_dark_theme(self):
        """Apply dark theme stylesheet."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 5px;
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #0078d4;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border: 2px solid #0078d4;
            }
            QListWidget {
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QListWidget::item {
                padding: 5px;
                color: #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
            QCheckBox {
                spacing: 5px;
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #888888;
                border-radius: 3px;
                background-color: #1e1e1e;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 2px solid #0078d4;
            }
            QListWidget::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #888888;
                border-radius: 3px;
                background-color: #1e1e1e;
            }
            QListWidget::indicator:checked {
                background-color: #0078d4;
                border: 2px solid #0078d4;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QToolBar {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3c3c3c;
                spacing: 3px;
                padding: 3px;
            }
            QToolButton {
                color: #e0e0e0;
                padding: 5px;
            }
            QStatusBar {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border-top: 1px solid #3c3c3c;
            }
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #5c5c5c;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6c6c6c;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #5c5c5c;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #6c6c6c;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3c3c3c;
            }
            QComboBox::drop-down {
                background-color: #3c3c3c;
                border-left: 1px solid #3c3c3c;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #0078d4;
                border: 1px solid #3c3c3c;
            }
        """)

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
        self.format_edit.setPlainText(self.config_data.get('format', ''))

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
            if self.schema_data and 'properties' in self.schema_data:
                module_schema = self.schema_data['properties'].get(module_name, {})
                schema_props = module_schema.get('properties', {})
                schema_description = module_schema.get('description', None)

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

        format_text = self.format_edit.toPlainText().strip()
        if format_text:
            self.config_data['format'] = format_text
        elif 'format' in self.config_data:
            del self.config_data['format']

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

    # === Schema Handling ===

    def _on_schema_loaded(self, schema: Dict):
        """Handle successful schema loading."""
        self.schema_data = schema
        self.status_bar.showMessage("✅ Schema loaded - enhanced fields available", 5000)

    def _on_schema_failed(self, error: str):
        """Handle schema loading failure."""
        self.status_bar.showMessage(f"⚠️ Schema unavailable: {error}", 5000)

    # === Utility Methods ===

    def _update_app_font_size(self, size: int):
        """Update the application-wide font size."""
        font = QFont("Sans Serif", size)
        QApplication.instance().setFont(font)
        self.status_bar.showMessage(f"Interface font size: {size}pt", 2000)

    def _update_code_font_size(self, size: int):
        """Update the code editor font size."""
        self.full_config_editor.setFont(QFont("Monospace", size))
        self.status_bar.showMessage(f"Code editor font size: {size}pt", 2000)

    def _toggle_theme(self):
        """Toggle between light and dark themes."""
        self.is_dark_mode = not self.is_dark_mode
        self._apply_theme()

        # Update menu and toolbar button text
        if self.is_dark_mode:
            self.theme_action.setText("☀️ Light Mode")
            self.theme_button.setText("☀️ Light Mode")
            self.status_bar.showMessage("🌙 Dark mode enabled", 2000)
        else:
            self.theme_action.setText("🌙 Dark Mode")
            self.theme_button.setText("🌙 Dark Mode")
            self.status_bar.showMessage("☀️ Light mode enabled", 2000)

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
