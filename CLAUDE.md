# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Starship Configurator is a cross-platform PyQt6 GUI application for configuring the Starship cross-shell prompt. It provides a user-friendly interface to read, edit, and write `starship.toml` configuration files.

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
- **System dependency**: `starship` must be installed and available in PATH for preview functionality

## Architecture and Key Design Patterns

### Main Components

**StarshipConfigurator (Main Window)**
- Loads config from `~/.config/starship.toml` on startup using `tomlkit` for lossless parsing
- Three-panel layout: sidebar (module list) + central area (stacked config panels) + bottom bar (actions)

**Configuration Management**
- `self.config_data`: tomlkit document object that preserves TOML structure, comments, and formatting
- `_update_config_from_gui()`: Syncs all GUI widget values back to the internal TOML document
- **Critical**: Always use `tomlkit` library (not standard `toml` or `tomllib`) to maintain lossless read/write operations

**UI Structure**
- **Sidebar** (`QListWidget`): Lists "Global Settings" plus common Starship modules
- **Stacked Widget** (`QStackedWidget`): Contains dynamically generated panels for each module
- **Module Panels**: Auto-generated with QCheckBox (enable/disable), QLineEdit (format, style, symbol)
- **Bottom Bar**: Preview display area + action buttons (Load, Preview, Save)

### Data Flow

1. **Load**: `_load_initial_config()` → parses TOML with tomlkit → populates `self.config_data`
2. **Display**: Module panels created with `_create_module_panel()` → widgets initialized from config_data
3. **Edit**: User modifies widgets in GUI
4. **Sync**: `_update_config_from_gui()` → reads all widgets → updates `self.config_data`
5. **Save**: Writes `config_data.as_string()` to `~/.config/starship.toml`

### Preview System Implementation

```python
# Preview workflow (in _generate_preview):
1. Write current config to /tmp/starship_temp.toml
2. Execute: starship print --config /tmp/starship_temp.toml
3. Capture stdout (contains ANSI escape codes)
4. Display in read-only QTextEdit
5. Clean up temp file
```

## Important Implementation Details

### Module Configuration

**Predefined Modules** (`STARSHIP_MODULES` constant):
```python
["character", "directory", "git_branch", "git_status", "time",
 "cmd_duration", "status", "python", "node", "rust", "aws", "gcloud"]
```

**Dynamic Widget Naming Convention**:
- Enable checkbox: `{module_name}_check`
- Format input: `{module_name}_format`
- Style input: `{module_name}_style`
- Symbol input: `{module_name}_symbol` (only for applicable modules)

### Global Settings Panel

The first panel (index 0) contains:
- `add_newline` checkbox for global config
- Advanced editor (`full_config_editor`): Direct TOML text editing as fallback

**Special behavior**: When saving from Global Settings view (row 0), the raw text from `full_config_editor` takes priority over structured GUI data.

### File Paths

- Default config location: `~/.config/starship.toml` (defined in `CONFIG_PATH`)
- Temporary preview config: `/tmp/starship_temp.toml`

## Starship Configuration Resources

When modifying or extending the application, reference these official Starship resources:

| Resource | URL |
|----------|-----|
| Configuration Documentation | https://starship.rs/config/ |
| JSON Schema (for validation) | https://starship.rs/config-schema.json |
| Presets (example configs) | https://starship.rs/presets/ |

## Code Structure

```
starship_configurator.py (330 lines)
├── Configuration Constants (lines 15-25)
├── StarshipConfigurator Class (lines 29-318)
│   ├── __init__: Initialize window, load config, build UI
│   ├── UI Building Methods (lines 72-183)
│   │   ├── _build_ui: Main layout construction
│   │   ├── _create_global_settings_panel
│   │   ├── _create_module_panel: Generic panel factory
│   │   └── _create_bottom_bar: Action buttons + preview
│   ├── Data Methods (lines 193-245)
│   │   └── _update_config_from_gui: Core sync logic
│   └── Action Methods (lines 247-318)
│       ├── _save_config: Write to starship.toml
│       ├── _load_config_from_file: Import external config
│       └── _generate_preview: Execute starship print
└── Application Entry Point (lines 323-330)
```

## Key Technical Constraints

1. **tomlkit dependency**: Required for preserving TOML structure and comments when saving
2. **Starship CLI dependency**: Preview feature requires `starship` binary in system PATH
3. **Widget state sync**: Must call `_update_config_from_gui()` before any save/preview operation
4. **Empty module cleanup**: Modules with no active fields are removed from config (line 240-241)
5. **Config directory creation**: Ensures `~/.config/` exists before writing (line 259)

## Extending the Application

### Adding New Modules
1. Add module name to `STARSHIP_MODULES` list (line 22-25)
2. Panel will be auto-generated with standard fields (format, style)
3. For custom fields (like symbol), add conditional logic in `_create_module_panel()` (line 149-156)

### Adding Module-Specific Fields
Extend the conditional blocks in:
- `_create_module_panel()`: Add widget creation logic
- `_update_config_from_gui()`: Add data sync logic for new field

### Schema-Driven Approach (Future Enhancement)
The `SCHEMA_URL` constant (line 19) points to Starship's JSON schema. A future improvement could fetch this schema and dynamically generate appropriate input widgets for each module's specific properties.
