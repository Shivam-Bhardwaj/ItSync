# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-05-12

### Added

* **Graphical User Interface (GUI):**
    * Main application window built with CustomTkinter.
    * Dialog for adding new sync tasks (source and multiple destinations).
    * Display list of configured tasks with status.
    * Buttons to add, remove selected, start selected, stop selected tasks.
    * Buttons to "Start All", "Stop All", and "Remove All" tasks.
* **Task Persistence:** Sync configurations are saved to `sync_config.json` and loaded on startup.
* **Background Syncing:** Each sync task runs in its own thread using `watchdog`.
* **Auto-Start:**
    * Tasks loaded from config attempt to start automatically on application launch.
    * Newly added tasks attempt to start automatically.
* **File Logging:** Logs are now written to `Documents/SyncAppLogs/sync_app.log` in addition to the console.
* **UI Enhancements:**
    * Improved font size for destination listbox in Add Task dialog.
    * Task selection highlighting in the main list.

### Changed

* Core logic adapted to work within the GUI and threading model.
* `update_task_display` now dynamically creates frames for each task.
* Refined stop/start logic for individual and all tasks.
* Improved error logging and status updates in the GUI.

## [0.2.0] - 2025-05-12

### Added

* Python command-line implementation using `watchdog` library for cross-platform real-time monitoring.
* Initial sync functionality using `shutil.copytree`.
* Handling for create, delete, modify, and move events.
* Command-line argument parsing for source and destination paths.
* Basic console logging.
* `.gitignore` file for Python projects.
* Example `push_script.sh` and `push_script.bat`.

### Changed

* Replaced previous C++ implementation attempt with Python version.
* Updated README and CHANGELOG for Python command-line implementation.

## [0.1.0] - 2025-05-12

### Added

* Initial C++ implementation concept using Windows API (`ReadDirectoryChangesW`) and `std::filesystem`. (Note: Encountered compilation issues).
* CMake build structure.
* Initial README and CHANGELOG for C++ version.
