# 💻 LLM Prompt: Starship Configurator GUI (PyQt6) Builder

**GOAL:** Create a functional, cross-platform GUI application using **Python (PyQt6)** that allows a user to configure the Starship cross-shell prompt by providing an intuitive interface to read, edit, and write the `starship.toml` configuration file. The resulting output MUST be the complete, runnable Python code for the application.

### 1. Application Structure and Requirements

| Component | Detail |
| :--- | :--- |
| **GUI Framework** | PyQt6 |
| **Language** | Python 3.9+ |
| **Staship Config File** | TOML (`~/.config/starship.toml`) |
| **Python Library** | `tomlkit` (Crucial for lossless reading/writing) |
| **Core Functionality**| 1. **Load** existing `starship.toml`. 2. **GUI Panels** for each Starship module. 3. **Live Preview** (using `starship print`). 4. **Save** changes back to the file. |

### 2. Required Python Libraries

The application must use the following Python libraries for data handling and the GUI:

1.  **`PyQt6`**: For all GUI elements (Windows, Widgets, Layouts).
2.  **`tomlkit`**: **Crucial.** Use this library to read and write the `starship.toml` file. This library is preferred over standard `toml` or `tomllib` because it is **lossless**, meaning it preserves comments, formatting, and the original structure of the TOML file when writing changes back.
3.  **`os` / `pathlib`**: For finding the default Starship config path: `~/.config/starship.toml`.
4.  **`subprocess`**: For executing Starship commands (specifically `starship print --config /tmp/temp_starship.toml` for the preview).

### 3. Core Functional Requirements (User Flow)

The application needs the following main sections:

#### 3.1 Main Window Layout

* A **Sidebar (QListWidget)** listing **Global Settings** and all common Starship modules (e.g., `character`, `directory`, `git_branch`, `python`, `time`).
* A **Central Area (QStackedWidget)** that displays the configuration fields for the currently selected module.
* A **Bottom Bar** for controls: **Load Config**, **Save Config**, and **Preview**.

#### 3.2 Module Configuration Area

For each module (e.g., `[git_branch]`), the panel must include:

* **Toggle:** A `QCheckBox` to enable/disable the module (sets `disabled = true/false`).
* **Format String:** A `QLineEdit` or `QTextEdit` for the module's `format` field.
* **Style String:** A `QLineEdit` for the `style` field (accepting strings like `bold red`).
* **Symbol:** A `QLineEdit` for the module's primary `symbol` (e.g., `symbol = " "`).

#### 3.3 The Preview System

* **Functionality:** The Preview Button must trigger the following sequence:
    1.  Write the current GUI settings to a **temporary** `starship.toml` file.
    2.  Execute the command `starship print --config /path/to/temp_starship.toml`.
    3.  Display the raw output (which contains ANSI escape codes) in a **read-only `QTextEdit`** in the GUI.

### 4. Technical Configuration Details and Resources

The implementation must be informed by the following official Starship resources:

| Resource Type | Detail | URL/Information |
| :--- | :--- | :--- |
| **Official Website** | Starship.rs homepage. | **[https://starship.rs/](https://starship.rs/)** |
| **Configuration Docs** | Comprehensive documentation for all modules and options. | **[https://starship.rs/config/](https://starship.rs/config/)** |
| **JSON Schema (Crucial)** | The schema for editor auto-completion. This structure should guide the GUI's data fields. | **[https://starship.rs/config-schema.json](https://starship.rs/config-schema.json)** |
| **Presets (Inspiration)** | List of pre-built configurations that can serve as excellent starting points or themes. | **[https://starship.rs/presets/](https://starship.rs/presets/)** |
| **Example Configs** | Real-world examples of `starship.toml` files to demonstrate complexity. | Search GitHub for `starship.toml` gists, e.g., **[https://gist.github.com/ryo-ARAKI/48a11585299f9032fa4bda60c9bba593](https://gist.github.com/ryo-ARAKI/48a11585299f9032fa4bda60c9bba593)** |
| **Key Config File** | The default location for Starship to load its configuration. | `~/.config/starship.toml` |

**The final output MUST be the complete, executable Python code for the PyQt6 application, enclosed in a single Python code block.**


you can start with the code already in this folder.