import sys
import time
import os
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, LoggingEventHandler

# --- Configuration ---
# Basic logging setup
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# --- Helper Functions ---

def sync_item(src_path, dest_path_root, relative_path):
    """Synchronizes a single item (file or directory) from source to one destination."""
    full_src_path = src_path
    full_dest_path = os.path.join(dest_path_root, relative_path)
    dest_parent_dir = os.path.dirname(full_dest_path)

    try:
        # Ensure destination parent directory exists
        if not os.path.exists(dest_parent_dir):
            os.makedirs(dest_parent_dir, exist_ok=True)
            logging.info(f"Created parent directory: {dest_parent_dir}")

        # Handle directory creation/sync
        if os.path.isdir(full_src_path):
            if not os.path.exists(full_dest_path):
                os.makedirs(full_dest_path, exist_ok=True)
                logging.info(f"Created directory: {full_dest_path}")
            # Note: shutil.copytree copies contents. For simple dir creation,
            # makedirs is sufficient. Event handler will catch content changes.
        # Handle file copy/sync
        elif os.path.isfile(full_src_path):
            shutil.copy2(full_src_path, full_dest_path) # copy2 preserves metadata
            logging.info(f"Copied: {full_src_path} to {full_dest_path}")

    except Exception as e:
        logging.error(f"Error syncing {full_src_path} to {full_dest_path}: {e}")

def delete_item(dest_path_root, relative_path):
    """Deletes an item (file or directory) from one destination."""
    full_dest_path = os.path.join(dest_path_root, relative_path)
    try:
        if os.path.isdir(full_dest_path):
            shutil.rmtree(full_dest_path)
            logging.info(f"Deleted directory: {full_dest_path}")
        elif os.path.isfile(full_dest_path):
            os.remove(full_dest_path)
            logging.info(f"Deleted file: {full_dest_path}")
        # else: item might already be deleted
    except Exception as e:
        logging.error(f"Error deleting {full_dest_path}: {e}")

def initial_sync(src_root, dest_roots):
    """Performs initial sync from source to all destinations."""
    logging.info(f"Starting initial sync from {src_root}...")
    for dest_root in dest_roots:
        logging.info(f"Syncing to destination: {dest_root}")
        try:
            # Remove destination if it exists to start fresh (optional, be careful!)
            # if os.path.exists(dest_root):
            #     logging.warning(f"Removing existing destination before sync: {dest_root}")
            #     shutil.rmtree(dest_root)

            # Copy the entire tree
            shutil.copytree(src_root, dest_root, dirs_exist_ok=True, copy_function=shutil.copy2)
            logging.info(f"Initial sync to {dest_root} complete.")
        except Exception as e:
            logging.error(f"Error during initial sync to {dest_root}: {e}")
    logging.info("Initial sync finished.")


# --- Watchdog Event Handler ---

class SyncEventHandler(FileSystemEventHandler):
    """Handles filesystem events and triggers sync/delete operations."""

    def __init__(self, source_root, destination_roots):
        super().__init__()
        self.source_root = os.path.abspath(source_root)
        self.destination_roots = [os.path.abspath(d) for d in destination_roots]
        logging.info(f"Handler initialized. Source: {self.source_root}")
        logging.info(f"Handler initialized. Destinations: {self.destination_roots}")

    def _get_relative_path(self, src_path):
        """Calculates the path relative to the source root."""
        return os.path.relpath(src_path, self.source_root)

    def on_created(self, event):
        """Called when a file or directory is created."""
        logging.info(f"Event - Created: {event.src_path} (Is Dir: {event.is_directory})")
        relative_path = self._get_relative_path(event.src_path)
        # Check existence again, might be temporary file
        if os.path.exists(event.src_path):
            for dest_root in self.destination_roots:
                sync_item(event.src_path, dest_root, relative_path)
        else:
             logging.warning(f"Source {event.src_path} not found shortly after creation event.")


    def on_deleted(self, event):
        """Called when a file or directory is deleted."""
        logging.info(f"Event - Deleted: {event.src_path} (Is Dir: {event.is_directory})")
        relative_path = self._get_relative_path(event.src_path)
        for dest_root in self.destination_roots:
            delete_item(dest_root, relative_path)

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        # NOTE: Modification events for directories are often less useful/reliable
        # We primarily care about file modifications.
        if not event.is_directory:
            logging.info(f"Event - Modified: {event.src_path}")
            relative_path = self._get_relative_path(event.src_path)
             # Check existence again
            if os.path.exists(event.src_path):
                for dest_root in self.destination_roots:
                    sync_item(event.src_path, dest_root, relative_path)
            else:
                logging.warning(f"Source {event.src_path} not found shortly after modification event.")


    def on_moved(self, event):
        """Called when a file or directory is moved or renamed."""
        logging.info(f"Event - Moved: {event.src_path} to {event.dest_path}")
        relative_path_old = self._get_relative_path(event.src_path)
        relative_path_new = self._get_relative_path(event.dest_path)

        # Check existence of new path
        new_path_exists = os.path.exists(event.dest_path)

        for dest_root in self.destination_roots:
            # Delete the old item in destination
            delete_item(dest_root, relative_path_old)
            # Sync the new item from source if it exists
            if new_path_exists:
                 sync_item(event.dest_path, dest_root, relative_path_new)
            else:
                 logging.warning(f"Source {event.dest_path} not found shortly after move event.")


# --- Main Execution ---

if __name__ == "__main__":
    # --- Argument Parsing ---
    if len(sys.argv) < 3:
        print("Usage: python real_time_sync.py <source_directory> <destination_directory_1> [<destination_directory_2> ...]")
        sys.exit(1)

    source_path = sys.argv[1]
    destination_paths = sys.argv[2:]

    # --- Validate Paths ---
    if not os.path.isdir(source_path):
        logging.error(f"Source directory '{source_path}' does not exist or is not a directory.")
        sys.exit(1)

    valid_destinations = []
    for dest_path in destination_paths:
        if not os.path.exists(dest_path):
            try:
                os.makedirs(dest_path, exist_ok=True)
                logging.info(f"Created destination directory: {dest_path}")
                valid_destinations.append(dest_path)
            except Exception as e:
                logging.error(f"Failed to create destination directory '{dest_path}': {e}")
        elif not os.path.isdir(dest_path):
            logging.error(f"Destination path '{dest_path}' exists but is not a directory.")
            # Optionally skip this destination or exit
        else:
            valid_destinations.append(dest_path) # It exists and is a directory

    if not valid_destinations:
         logging.error("No valid destination directories specified or could be created.")
         sys.exit(1)

    # --- Initial Sync ---
    initial_sync(source_path, valid_destinations)

    # --- Setup Watchdog Observer ---
    event_handler = SyncEventHandler(source_path, valid_destinations)
    observer = Observer()
    observer.schedule(event_handler, source_path, recursive=True)

    # --- Start Monitoring ---
    observer.start()
    logging.info(f"Monitoring started on '{source_path}'. Press Ctrl+C to stop.")

    try:
        while True:
            # Keep the main thread alive
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping observer...")
        observer.stop()
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        observer.stop()

    # Wait for the observer thread to finish
    observer.join()
    logging.info("Monitoring stopped.")
