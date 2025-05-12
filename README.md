# Python Real-Time Directory Sync

A command-line utility for Windows, macOS, and Linux that provides real-time, one-way synchronization from a source directory to one or more destination directories. It's written in Python and utilizes the `watchdog` library for efficient cross-platform directory monitoring.

## Overview

This tool monitors a specified source directory for any changes to its files and subdirectories (creations, deletions, modifications, renames/moves). When a change is detected, it's replicated to all specified destination directories, keeping them in sync with the source in real-time. An initial synchronization is performed when the tool starts to ensure destination directories match the source.

## Features

* **Real-time Monitoring:** Uses the `watchdog` library for efficient, cross-platform monitoring.
* **One-Way Sync:** Synchronizes changes from one source to multiple destinations.
* **Subdirectory Support:** Recursively monitors and syncs subdirectories.
* **Initial Synchronization:** Ensures destinations are brought up-to-date with the source upon startup using `shutil.copytree`.
* **Handles Common File Operations:** Create, Delete, Modify, Move/Rename.
* **Basic Logging:** Outputs actions and errors to the console.
* **Command-Line Interface:** Simple and scriptable.

## Requirements

* Python 3.6+
* `watchdog` library

## Installation

1.  **Clone or download the repository/script.**
2.  **Install the `watchdog` library:**
    Open your terminal or command prompt and run:
    ```bash
    pip install watchdog
    ```
    *(You might need to use `pip3` depending on your Python installation).*

## How to Run

Execute the script from your terminal or command prompt:

```bash
python real_time_sync.py <source_directory> <destination_directory_1> [<destination_directory_2> ...]