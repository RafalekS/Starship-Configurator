# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Starship Configurator is a modern, cross-platform PyQt6 GUI application for configuring the Starship cross-shell prompt. It provides an intuitive, feature-rich interface to read, edit, and write `starship.toml` configuration files with schema-driven widget generation.

## Running the Application

### Installation
```bash
# Install required dependencies
pip install PyQt6 tomlkit
```

### Launch
```bash
# Run the GUI application
python starship_configurator.py
```

### Requirements
- **Python**: 3.9 or higher
- **Dependencies**: PyQt6, tomlkit
- **System dependency**: `starship` must be installed and available in PATH for preview functionality

## Architecture and Key Design Patterns

### Main Components

**StarshipConfigurator (Main Window)**
- Auto-detects config location across platforms (Windows/Linux/macOS)
- Modern three-panel layout with resizable splitter: sidebar + config panel + bottom preview
- Menu bar, toolbar, and status bar for full-featured application experience
- Background thread for schema fetching to avoid blocking UI

**Configuration Path Detection** (`detect_starship_config_path()`)
- Checks `STARSHIP_CONFIG` environment variable first
- Platform-specific fallbacks:
  - **Windows**: `~/.config/starship.toml`, `%APPDATA%/starship/starship.toml`, `~/starship.toml`
  - **Linux/macOS**: `~/.config/starship.toml`, `$XDG_CONFIG_HOME/starship.toml`
- Returns first existing path or defaults to `~/.config/starship.toml`

**Schema-Driven Widget Generation**
- `SchemaFetcher` thread fetches JSON schema from starship.rs in background
- `_create_widget_for_schema()` generates appropriate widgets based on property types:
  - `boolean` → QCheckBox
  - `integer` → QSpinBox with min/max ranges
  - `array` → QTextEdit (multi-line input)
  - `string` → QLineEdit with placeholder hints
- Automatically creates module-specific fields from schema properties

**UI Structure**
- **Left Panel**:
  - Search box for filtering modules
  - Category selector (Common/All/Active modules)
  - Dynamic module list with status icons (✅ active, 📦 available)
  - Config path display with tooltip
- **Right Panel** (QStackedWidget):
  - Global Settings panel (index 0)
  - Dynamically created module panels (lazy-loaded on selection)
  - Scroll areas for long configurations
  - Grouped settings (Common Settings, Module-Specific Settings)
- **Bottom Panel**:
  - Preview area with monospace font
  - Action buttons: Preview, Save, Export

### Data Flow

1. **Startup**: `detect_starship_config_path()` → `_load_initial_config()` → `_populate_ui_from_config()`
2. **Schema Loading**: Background `SchemaFetcher` thread → `_on_schema_loaded()` signal
3. **Module Selection**: User clicks module → `_on_module_selected()` → `_show_module_panel()` (lazy creation)
4. **Edit**: User modifies widgets in GUI
5. **Sync**: `_update_config_from_gui()` → reads all widgets → updates `self.config_data`
6. **Save**: Writes `config_data.as_string()` to detected config path
7. **Preview**: Temp file → `starship print --config` → display output

### Advanced Features

**Module Management**
- 90+ Starship modules supported (complete list in `STARSHIP_MODULES`)
- Common modules highlighted (`COMMON_MODULES`)
- Active module filtering
- Live search/filter
- Lazy panel creation (only creates panels when modules are selected)

**Configuration Flexibility**
- Direct TOML editing with "Reload from TOML" button
- Load/Save from arbitrary files
- Export configurations
- Preserves TOML structure, comments, and formatting via `tomlkit`

**Cross-Platform Temp Files**
- Uses `tempfile.NamedTemporaryFile()` for platform-agnostic temp file handling
- Auto-cleanup in finally block

## Important Implementation Details

### Module Widget Storage

**Dynamic Widget Registry** (`self.module_widgets`):
```python
{
  'module_name': {
    'enabled': QCheckBox,
    'fields': {
      'format': QLineEdit,
      'style': QLineEdit,
      'disabled': QCheckBox,
      'symbol': QLineEdit,  # schema-driven fields
      ...
    }
  }
}
```

### Global Settings

Configured in `_create_global_settings_panel()`:
- `add_newline` (bool)
- `scan_timeout` (int, milliseconds)
- `command_timeout` (int, milliseconds)
- `format` (custom prompt format string)
- Full TOML editor (advanced users)

### Styling System

Modern CSS-like stylesheet in `_apply_styles()`:
- Blue accent color (#0078d4) for buttons and focus states
- Hover effects on buttons and list items
- Rounded corners and consistent padding
- Light gray background (#f5f5f5)
- GroupBox styling with proper title positioning

### File Paths

- **Config detection**: See `detect_starship_config_path()` function
- **Temp files**: `tempfile.NamedTemporaryFile()` for cross-platform compatibility
- **Encoding**: UTF-8 for all file operations

## Code Structure

```
starship_configurator.py (968 lines)
├── Imports (lines 1-19)
├── Constants (lines 21-48)
│   ├── SCHEMA_URL
│   ├── STARSHIP_MODULES (90+ modules)
│   └── COMMON_MODULES (19 popular modules)
├── Helper Functions (lines 51-77)
│   └── detect_starship_config_path(): Platform-aware config detection
├── SchemaFetcher Thread (lines 80-94)
│   └── Background JSON schema fetching
└── StarshipConfigurator Class (lines 99-945)
    ├── __init__: Initialize window, detect config, build UI, start schema thread
    ├── UI Building Methods (lines 127-575)
    │   ├── _build_ui: Main layout with splitter
    │   ├── _create_module_list_panel: Search + category + list
    │   ├── _create_config_panel: Stacked widget container
    │   ├── _create_global_settings_panel: Global config UI
    │   ├── _create_module_panel: Schema-driven panel generation
    │   ├── _create_widget_for_schema: Type-based widget factory
    │   ├── _create_bottom_panel: Preview + actions
    │   ├── _create_menu_bar: File/Edit/Help menus
    │   ├── _create_toolbar: Quick action buttons
    │   ├── _create_status_bar: Status messages
    │   └── _apply_styles: Modern CSS stylesheet
    ├── Configuration Management (lines 577-790)
    │   ├── _load_initial_config: Load or create config
    │   ├── _create_default_config: Minimal starter config
    │   ├── _populate_ui_from_config: Sync config → UI
    │   ├── _update_full_editor: Refresh TOML editor
    │   ├── _update_module_list: Dynamic module list
    │   ├── _filter_modules: Search implementation
    │   ├── _on_module_selected: Handle module clicks
    │   ├── _show_module_panel: Lazy panel creation
    │   ├── _load_module_config: Load module data into widgets
    │   └── _update_config_from_gui: Sync UI → config
    ├── Action Methods (lines 792-915)
    │   ├── _save_config: Save to starship.toml
    │   ├── _export_config: Export to custom file
    │   ├── _load_config_from_file: Import config
    │   ├── _reload_config: Reload from disk
    │   ├── _reload_from_toml_editor: Parse TOML editor
    │   └── _generate_preview: Execute starship print
    ├── Schema Handling (lines 917-926)
    │   ├── _on_schema_loaded: Process fetched schema
    │   └── _on_schema_failed: Handle fetch errors
    └── Utility Methods (lines 928-945)
        ├── _open_url: External browser
        └── _show_about: About dialog
```

## Key Technical Constraints

1. **tomlkit dependency**: Required for preserving TOML structure, comments, and formatting
2. **Starship CLI dependency**: Preview requires `starship` binary in PATH
3. **Schema fetching**: Background thread prevents UI blocking, gracefully handles failures
4. **Lazy loading**: Module panels created on-demand to reduce initial load time
5. **Widget state sync**: `_update_config_from_gui()` must be called before save/preview
6. **Cross-platform paths**: Uses `Path()` and `tempfile` for OS compatibility
7. **UTF-8 encoding**: All file operations use explicit UTF-8 encoding

## Critical Import Requirements

**IMPORTANT: PyQt6 Widget Imports**

The application uses a **tabbed interface** (`QTabWidget`). When modifying the UI code, ensure these imports are present:

```python
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLineEdit, QCheckBox, QPushButton,
    QTextEdit, QLabel, QFileDialog, QMessageBox, QGridLayout,
    QScrollArea, QGroupBox, QComboBox, QSpinBox, QListWidgetItem,
    QToolBar, QStatusBar, QSplitter, QTabWidget  # ← MUST INCLUDE QTabWidget!
)
```

**Common Error**: Forgetting `QTabWidget` will cause `NameError: name 'QTabWidget' is not defined`

This is the main UI container for the 4-tab layout (Modules, Global Settings, Preview, TOML Editor).

## Extending the Application

### Adding New Modules

Modules are auto-discovered from `STARSHIP_MODULES` list:
1. Add module name to `STARSHIP_MODULES` (line 26-40)
2. Optionally add to `COMMON_MODULES` if frequently used (line 43-48)
3. Panel will be auto-generated with schema-based fields
4. No other code changes required

### Adding Custom Widget Types

Extend `_create_widget_for_schema()` (line 378-404):
```python
elif prop_type == 'color':
    widget = QColorDialog()
    # Add color picker logic
    return widget
```

### Customizing UI Theme

Modify `_apply_styles()` (line 509-575):
- Change accent color (#0078d4)
- Adjust padding/margins
- Update hover effects
- Modify font sizes

### Adding Preset Configurations

Create a new method to load preset configs:
```python
def _load_preset(self, preset_name: str):
    preset_url = f'https://starship.rs/presets/{preset_name}.toml'
    # Fetch and load preset
```

## Starship Configuration Resources

| Resource | URL |
|----------|-----|
| Configuration Documentation | https://starship.rs/config/ |
| JSON Schema (auto-loaded) | https://starship.rs/config-schema.json |
| Presets (example configs) | https://starship.rs/presets/ |
| Module Documentation | https://starship.rs/config/#modules |

## Performance Optimizations

1. **Lazy Panel Creation**: Module panels only created when selected (not all 90+ upfront)
2. **Background Schema Fetching**: Non-blocking network request
3. **Efficient Widget Lookup**: Dictionary-based widget registry (`self.module_widgets`)
4. **Minimal Redraws**: QStackedWidget shows/hides panels without recreation
5. **Search Optimization**: List filtering done in Python (fast for 90 items)

## Known Limitations

1. **ANSI Preview**: Preview shows ANSI codes as text (Qt doesn't render ANSI natively)
2. **Schema Fields Limit**: Only first 10 schema fields shown per module to avoid UI clutter
3. **No Undo/Redo**: Changes are applied immediately (use "Reload from Disk" to revert)
4. **Single Instance**: No inter-instance communication or file locking
