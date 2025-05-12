# Python Real-Time Directory Sync GUI

A user-friendly desktop application for Windows, macOS, and Linux that provides real-time, one-way synchronization from source directories to one or more destination directories. It's written in Python, using `CustomTkinter` for the graphical user interface and the `watchdog` library for efficient cross-platform directory monitoring.

## Overview

This tool allows users to easily configure and manage multiple synchronization tasks. Each task monitors a specified source directory for changes (creations, deletions, modifications, renames/moves). When a change is detected, it's replicated to all specified destination directories for that task. An initial synchronization is performed when a task starts. Tasks are saved and automatically started when the application launches.

## Features

* **Graphical User Interface:** Built with CustomTkinter for a modern look and feel.
* **Task Management:**
    * Add new sync tasks with a dedicated dialog (select source, add multiple destinations).
    * View a list of configured tasks with their status (Stopped, Starting, Syncing, Running, Error).
    * Select individual tasks to start or stop them.
    * Remove selected tasks or all tasks with confirmation.
* **Real-time Monitoring:** Uses the `watchdog` library for efficient, cross-platform monitoring.
* **One-Way Sync:** Synchronizes changes from one source to multiple destinations per task.
* **Subdirectory Support:** Recursively monitors and syncs subdirectories.
* **Initial Synchronization:** Ensures destinations are brought up-to-date with the source when a task starts.
* **Handles Common File Operations:** Create, Delete, Modify, Move/Rename.
* **Persistent Configuration:** Sync tasks are saved to a `sync_config.json` file and reloaded on startup.
* **Auto-Start Tasks:** Configured tasks attempt to start automatically when the application launches. Newly added tasks also auto-start.
* **Logging:**
    * Outputs actions and errors to the console.
    * Logs to a file (`sync_app.log`) in a `SyncAppLogs` folder within the user's Documents directory.
* **Background Operation:** Sync tasks run in separate threads to keep the GUI responsive.

## Requirements

* Python 3.6+
* `customtkinter` library
* `watchdog` library

## Installation

1.  **Clone or download the repository/script.**
2.  **Install the required libraries:**
    Open your terminal or command prompt and run:
    ```bash
    pip install customtkinter watchdog
    ```
    *(You might need to use `pip3` depending on your Python installation).*

## How to Run

Execute the main Python script (e.g., `sync_app.py`) from your terminal or command prompt:

```bash
python sync_app.py