import sys
import os
import subprocess
from pathlib import Path

# Third-party libraries
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLineEdit, QCheckBox, QPushButton,
    QTextEdit, QLabel, QFileDialog, QMessageBox, QTabWidget, QGridLayout
)
from PyQt6.QtCore import Qt
import tomlkit

# --- Configuration Constants ---

# Default path for starship.toml
CONFIG_PATH = Path.home() / ".config" / "starship.toml"
SCHEMA_URL = '[https://starship.rs/config-schema.json](https://starship.rs/config-schema.json)'

# Basic Starship Modules for Sidebar
STARSHIP_MODULES = [
    "character", "directory", "git_branch", "git_status", "time", 
    "cmd_duration", "status", "python", "node", "rust", "aws", "gcloud"
]

# --- Main Application Window ---

class StarshipConfigurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Starship Configurator")
        self.setGeometry(100, 100, 1000, 700)
        
        # Internal configuration storage using tomlkit
        self.config_data = self._load_initial_config()

        self._build_ui()
        self._connect_signals()
        
    def _load_initial_config(self):
        """Loads the starship.toml file or creates a default structure."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    doc = tomlkit.load(f)
                    QMessageBox.information(self, "Load Success", f"Configuration loaded from:\n{CONFIG_PATH}")
                    return doc
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Could not load TOML file: {e}")
                return self._create_default_config()
        else:
            QMessageBox.information(self, "New Config", f"No config found at {CONFIG_PATH}. Creating default.")
            return self._create_default_config()

    def _create_default_config(self):
        """Creates a basic TOML document with the schema reference."""
        doc = tomlkit.document()
        # Add the official JSON Schema for editor support
        doc.add('$', tomlkit.string(SCHEMA_URL))
        doc['add_newline'] = True
        
        # Add basic character module
        doc.add(tomlkit.comment("Configuration for the prompt symbol"))
        char_table = tomlkit.table()
        char_table['success_symbol'] = "[❯](bold green)"
        char_table['error_symbol'] = "[❯](bold red)"
        doc['character'] = char_table
        
        return doc

    # --- UI Building Methods ---
    
    def _build_ui(self):
        """Sets up the main layout and widgets."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # 1. Sidebar (Module List)
        self.module_list = QListWidget()
        self.module_list.setFixedWidth(180)
        self.module_list.addItems(["-- Global Settings --"] + STARSHIP_MODULES)
        main_layout.addWidget(self.module_list)

        # 2. Stacked Widget (Config Panels)
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # Create config panels for each module
        self.config_panels = {}
        self._create_global_settings_panel()
        for module_name in STARSHIP_MODULES:
            self._create_module_panel(module_name)
            
        self._create_bottom_bar()

    def _create_global_settings_panel(self):
        """Panel for global settings like schema, newline, and all prompts."""
        panel = QWidget()
        layout = QGridLayout(panel)
        
        # Add Newline
        self.add_newline_check = QCheckBox("Add Newline before prompt")
        self.add_newline_check.setChecked(self.config_data.get('add_newline', True))
        layout.addWidget(self.add_newline_check, 0, 0, 1, 2)
        
        # Full TOML Editor (Fallback/Advanced)
        layout.addWidget(QLabel("Advanced: Full TOML Configuration"), 2, 0, 1, 2)
        self.full_config_editor = QTextEdit()
        self.full_config_editor.setPlainText(self.config_data.as_string())
        layout.addWidget(self.full_config_editor, 3, 0, 1, 2)

        self.stacked_widget.addWidget(panel)
        self.config_panels["-- Global Settings --"] = panel
        
    def _create_module_panel(self, name):
        """Creates a generic configuration panel for a Starship module."""
        panel = QWidget()
        layout = QGridLayout(panel)
        row = 0

        # Checkbox to disable module
        check_box = QCheckBox(f"Enable [{name}] Module")
        check_box.setChecked(name in self.config_data and self.config_data[name].get('disabled', False) is not True)
        layout.addWidget(check_box, row, 0, 1, 2)
        setattr(self, f"{name}_check", check_box)
        row += 1

        # Format field (most important)
        layout.addWidget(QLabel(f"Format String ({name}):"), row, 0)
        format_input = QLineEdit()
        if name in self.config_data:
            format_input.setText(self.config_data[name].get('format', ''))
        layout.addWidget(format_input, row, 1)
        setattr(self, f"{name}_format", format_input)
        row += 1
        
        # Style field
        layout.addWidget(QLabel(f"Style String ({name}):"), row, 0)
        style_input = QLineEdit()
        if name in self.config_data:
            style_input.setText(self.config_data[name].get('style', ''))
        layout.addWidget(style_input, row, 1)
        setattr(self, f"{name}_style", style_input)
        row += 1

        # Symbol field (if applicable)
        if name in ["character", "git_branch", "python", "node"]:
            layout.addWidget(QLabel(f"Symbol ({name}):"), row, 0)
            symbol_input = QLineEdit()
            if name in self.config_data:
                symbol_input.setText(self.config_data[name].get('symbol', ''))
            layout.addWidget(symbol_input, row, 1)
            setattr(self, f"{name}_symbol", symbol_input)
            row += 1

        layout.setRowStretch(row, 1) # Push content to top

        self.stacked_widget.addWidget(panel)
        self.config_panels[name] = panel
        
    def _create_bottom_bar(self):
        """Creates buttons for save, load, and preview."""
        bottom_bar = QWidget()
        h_layout = QHBoxLayout(bottom_bar)
        
        self.preview_text = QTextEdit()
        self.preview_text.setPlaceholderText("Starship Preview will appear here (may not show full colors).")
        self.preview_text.setReadOnly(True)
        self.preview_text.setFixedHeight(60)

        self.save_button = QPushButton("💾 Save Config")
        self.load_button = QPushButton("📂 Load from File")
        self.preview_button = QPushButton("✨ Generate Preview")
        
        h_layout.addWidget(self.preview_text)
        h_layout.addWidget(self.load_button)
        h_layout.addWidget(self.preview_button)
        h_layout.addWidget(self.save_button)

        main_layout = self.centralWidget().layout()
        main_layout.addWidget(bottom_bar)

    # --- Signal Connections ---
    
    def _connect_signals(self):
        self.module_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.save_button.clicked.connect(self._save_config)
        self.load_button.clicked.connect(self._load_config_from_file)
        self.preview_button.clicked.connect(self._generate_preview)
        
    # --- Data Handling Methods ---

    def _update_config_from_gui(self):
        """Reads data from all GUI elements and updates the internal TOML document."""
        
        # 1. Update Global Settings
        self.config_data['add_newline'] = self.add_newline_check.isChecked()
        
        # 2. Update Modules
        for name in STARSHIP_MODULES:
            is_enabled = getattr(self, f"{name}_check").isChecked()
            format_text = getattr(self, f"{name}_format").text().strip()
            style_text = getattr(self, f"{name}_style").text().strip()
            
            # Use tomlkit to manage table existence
            if name not in self.config_data and (is_enabled or format_text or style_text):
                 self.config_data[name] = tomlkit.table()
                 
            if name in self.config_data:
                module_table = self.config_data[name]
                
                # Update enablement
                if not is_enabled:
                    module_table['disabled'] = True
                elif 'disabled' in module_table:
                    del module_table['disabled']

                # Update main properties
                if format_text:
                    module_table['format'] = format_text
                elif 'format' in module_table:
                    del module_table['format']
                    
                if style_text:
                    module_table['style'] = style_text
                elif 'style' in module_table:
                    del module_table['style']
                    
                # Update symbol (if widget exists)
                if hasattr(self, f"{name}_symbol"):
                    symbol_text = getattr(self, f"{name}_symbol").text().strip()
                    if symbol_text:
                        module_table['symbol'] = symbol_text
                    elif 'symbol' in module_table:
                        del module_table['symbol']
                        
                # Remove module table if it's empty after updates
                if not module_table and name != 'character':
                    del self.config_data[name]

        # 3. Advanced Editor Sync (Write from GUI to editor for display)
        self.full_config_editor.setPlainText(self.config_data.as_string())


    def _save_config(self):
        """Saves the current configuration to starship.toml."""
        self._update_config_from_gui()
        
        try:
            # Final check: prioritize full editor content if the tab is active
            if self.module_list.currentRow() == 0:
                final_output = self.full_config_editor.toPlainText()
            else:
                final_output = self.config_data.as_string()
                
            # Ensure the directory exists
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            with open(CONFIG_PATH, 'w') as f:
                f.write(final_output)
            
            QMessageBox.information(self, "Save Success", f"Configuration successfully saved to:\n{CONFIG_PATH}\n\nRestart your terminal to see changes!")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file: {e}")

    def _load_config_from_file(self):
        """Opens a file dialog to load an existing TOML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Starship Config", str(CONFIG_PATH.parent), "TOML Files (*.toml);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    new_data = tomlkit.load(f)
                    self.config_data = new_data
                    QMessageBox.information(self, "Load Success", f"Loaded new configuration from:\n{file_path}")
                    # Rebuild the UI elements with new data
                    self.close()
                    self.__init__()
                    self.show()
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Could not load TOML file: {e}")

    def _generate_preview(self):
        """Executes 'starship print' with a temporary config for preview."""
        self._update_config_from_gui()
        temp_config_path = Path("/tmp/starship_temp.toml") # Use /tmp for cross-platform
        
        try:
            # 1. Write current config to a temporary file
            with open(temp_config_path, 'w') as f:
                f.write(self.config_data.as_string())

            # 2. Execute starship print command
            # Note: This requires 'starship' to be in the system PATH
            process = subprocess.run(
                ['starship', 'print', '--config', str(temp_config_path)],
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            
            # 3. Display the raw output (will contain ANSI codes)
            self.preview_text.setPlainText(process.stdout.strip())
            
        except FileNotFoundError:
            self.preview_text.setPlainText("ERROR: 'starship' command not found. Please ensure Starship is installed and in your system PATH.")
        except subprocess.CalledProcessError as e:
            self.preview_text.setPlainText(f"ERROR executing starship:\n{e.stderr}")
        except Exception as e:
            self.preview_text.setPlainText(f"An unexpected error occurred: {e}")
        finally:
            if temp_config_path.exists():
                os.remove(temp_config_path)


# --- Application Entry Point ---

if __name__ == '__main__':
    # Ensure a proper system font is used for symbols if not a Nerd Font
    # The user must still configure a Nerd Font in their terminal/Windows Terminal for the final output.
    
    app = QApplication(sys.argv)
    window = StarshipConfigurator()
    window.show()
    sys.exit(app.exec())