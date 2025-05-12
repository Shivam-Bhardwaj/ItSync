# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-05-12

### Added

* Python implementation using `watchdog` library for cross-platform real-time monitoring.
* Initial sync functionality using `shutil.copytree`.
* Handling for create, delete, modify, and move events.
* Command-line argument parsing for source and destination paths.
* Basic console logging.
* `.gitignore` file for Python projects.
* Example `push_script.sh`.

### Changed

* Replaced previous C++ implementation attempt with Python version.
* Updated README and CHANGELOG for Python implementation.

## [0.1.0] - 2025-05-12

### Added

* Initial C++ implementation concept using Windows API (`ReadDirectoryChangesW`) and `std::filesystem`. (Note: Encountered compilation issues).
* CMake build structure.
* Initial README and CHANGELOG for C++ version.
