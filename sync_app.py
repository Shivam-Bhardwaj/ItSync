import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, font as tkfont # Added tkfont
import os
import json
import threading # For running sync tasks in background
import time
import uuid
import logging # Import logging
import logging.handlers # For file handler
import shutil # For initial sync and file operations
from watchdog.observers import Observer # Watchdog imports
from watchdog.events import FileSystemEventHandler

# --- Configuration ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "sync_config.json"
LOG_DIR_NAME = "SyncAppLogs" # Folder within Documents
LOG_FILE_NAME = "sync_app.log"

# --- Setup Logging ---
def setup_logging():
    """Sets up console and file logging."""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

    try:
        documents_path = os.path.join(os.path.expanduser('~'), 'Documents')
        log_dir = os.path.join(documents_path, LOG_DIR_NAME)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        log_file_path = os.path.join(log_dir, LOG_FILE_NAME)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)
        logging.info(f"Logging to file: {log_file_path}")
    except Exception as e:
        logging.error(f"Failed to set up file logging: {e}")

# --- Helper Functions (Unchanged) ---

def sync_item(src_path, dest_path_root, relative_path, app_instance=None, task_id=None):
    full_src_path = src_path
    full_dest_path = os.path.join(dest_path_root, relative_path)
    dest_parent_dir = os.path.dirname(full_dest_path)
    log_prefix = f"[Task {task_id}] " if task_id else ""

    try:
        if not os.path.exists(full_src_path):
            logging.warning(f"{log_prefix}Source {full_src_path} disappeared before sync.")
            return

        if not os.path.exists(dest_parent_dir):
            if dest_parent_dir != dest_path_root and dest_parent_dir:
                 try:
                     os.makedirs(dest_parent_dir, exist_ok=True)
                     logging.info(f"{log_prefix}Created parent directory: {dest_parent_dir}")
                 except OSError as e:
                     logging.error(f"{log_prefix}Failed to create parent directory {dest_parent_dir}: {e}")
                     return

        if os.path.isdir(full_src_path):
            if not os.path.exists(full_dest_path):
                try:
                    os.makedirs(full_dest_path, exist_ok=True)
                    logging.info(f"{log_prefix}Created directory: {full_dest_path}")
                except OSError as e:
                     logging.error(f"{log_prefix}Failed to create directory {full_dest_path}: {e}")
        elif os.path.isfile(full_src_path):
            try:
                if os.path.isdir(full_dest_path):
                     logging.warning(f"{log_prefix}Destination {full_dest_path} is a directory, removing before copying file.")
                     shutil.rmtree(full_dest_path)
                shutil.copy2(full_src_path, full_dest_path)
                logging.info(f"{log_prefix}Copied: {os.path.basename(full_src_path)} to {dest_path_root}")
            except Exception as e:
                 logging.error(f"{log_prefix}Failed to copy file {full_src_path} to {full_dest_path}: {e}")

    except Exception as e:
        logging.error(f"{log_prefix}Error syncing {full_src_path} to {full_dest_path}: {e}")
        if app_instance:
             app_instance.after(0, app_instance.update_task_status, task_id, f"Error: Sync failed")

def delete_item(dest_path_root, relative_path, app_instance=None, task_id=None):
    full_dest_path = os.path.join(dest_path_root, relative_path)
    log_prefix = f"[Task {task_id}] " if task_id else ""
    try:
        if os.path.lexists(full_dest_path):
            if os.path.isdir(full_dest_path) and not os.path.islink(full_dest_path):
                shutil.rmtree(full_dest_path)
                logging.info(f"{log_prefix}Deleted directory: {full_dest_path}")
            else:
                os.remove(full_dest_path)
                logging.info(f"{log_prefix}Deleted file/link: {full_dest_path}")
    except Exception as e:
        logging.error(f"{log_prefix}Error deleting {full_dest_path}: {e}")
        if app_instance:
             app_instance.after(0, app_instance.update_task_status, task_id, f"Error: Delete failed")

# --- Watchdog Event Handler (Unchanged) ---
class SyncEventHandler(FileSystemEventHandler):
    def __init__(self, task_id, source_root, destination_roots, app_instance):
        super().__init__()
        self.task_id = task_id
        self.source_root = os.path.abspath(source_root)
        self.destination_roots = [os.path.abspath(d) for d in destination_roots]
        self.app = app_instance
        self.log_prefix = f"[Task {self.task_id}] "
        logging.info(f"{self.log_prefix}EventHandler initialized for source: {self.source_root}")

    def _get_relative_path(self, src_path):
        src_path_norm = os.path.normpath(src_path)
        source_root_norm = os.path.normpath(self.source_root)
        if src_path_norm == source_root_norm:
            return "."
        try:
            if not src_path_norm.startswith(source_root_norm + os.sep) and src_path_norm != source_root_norm :
                 logging.warning(f"{self.log_prefix}Event path {src_path_norm} seems outside source root {source_root_norm}. Ignoring.")
                 return None
            return os.path.relpath(src_path_norm, source_root_norm)
        except ValueError as e:
            logging.error(f"{self.log_prefix}Could not get relative path for {src_path_norm} based on {source_root_norm}: {e}")
            return None

    def process(self, event_type, event):
        src_path = getattr(event, 'src_path', None)
        dest_path = getattr(event, 'dest_path', None)

        if event.is_directory and event_type == "modified":
            logging.debug(f"{self.log_prefix}Ignoring directory modification: {src_path}")
            return
        if src_path and os.path.abspath(src_path) == self.source_root and event_type not in ["deleted", "moved_from"]:
            logging.debug(f"{self.log_prefix}Ignoring event on source root directory itself: {event_type} {src_path}")
            return

        logging.debug(f"{self.log_prefix}Raw Event: type={event_type}, src={src_path}, dest={dest_path}, is_dir={event.is_directory}")

        path_to_process = src_path
        relative_path = None
        relative_path_del = None

        if event_type.startswith("moved"):
             relative_path_del = self._get_relative_path(src_path)
             path_to_process = dest_path
             relative_path = self._get_relative_path(path_to_process)
        else:
             path_to_process = src_path
             relative_path = self._get_relative_path(path_to_process)
             relative_path_del = relative_path

        if relative_path is None and not event_type == "deleted":
             if not (event_type == "moved_from" and relative_path_del is not None):
                logging.warning(f"{self.log_prefix}Could not determine relative path for {path_to_process}. Skipping event.")
                return

        logging.info(f"{self.log_prefix}{event_type.capitalize()}: {relative_path if relative_path is not None else 'N/A'}"
                     f"{' -> ' + self._get_relative_path(dest_path) if event_type.startswith('moved') and dest_path else ''}"
                     f" (Is Dir: {event.is_directory})")

        if event_type == "deleted" or event_type == "moved_from":
            if relative_path_del is None:
                 logging.warning(f"{self.log_prefix}Cannot process delete/move_from for invalid relative path from {src_path}.")
                 return
            for dest_root in self.destination_roots:
                self.app.after(0, delete_item, dest_root, relative_path_del, self.app, self.task_id)
        elif event_type == "created" or event_type == "modified" or event_type == "moved_to":
            if relative_path is None:
                 logging.warning(f"{self.log_prefix}Cannot process create/modify/move_to for invalid relative path from {path_to_process}.")
                 return
            if os.path.exists(path_to_process): # Check existence before syncing
                 for dest_root in self.destination_roots:
                     self.app.after(0, sync_item, path_to_process, dest_root, relative_path, self.app, self.task_id)
            else:
                 logging.warning(f"{self.log_prefix}Source {path_to_process} not found shortly after {event_type} event.")

    def on_created(self, event):
        logging.debug(f"{self.log_prefix}on_created triggered for: {event.src_path}")
        self.process("created", event)

    def on_deleted(self, event):
        logging.debug(f"{self.log_prefix}on_deleted triggered for: {event.src_path}")
        self.process("deleted", event)

    def on_modified(self, event):
        if not event.is_directory:
            logging.debug(f"{self.log_prefix}on_modified triggered for file: {event.src_path}")
            self.process("modified", event)
        else:
            logging.debug(f"{self.log_prefix}Ignoring on_modified for directory: {event.src_path}")

    def on_moved(self, event):
        logging.debug(f"{self.log_prefix}on_moved triggered: {event.src_path} -> {event.dest_path}")
        self.process("moved_from", event)
        self.process("moved_to", event)

# --- Add Task Dialog Class ---
class AddTaskDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent

        self.title("Add New Sync Task")
        self.geometry("600x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.source_path = tk.StringVar()
        self.current_destinations = []

        # **MODIFIED:** Use a CTkFont for the Listbox to match other widgets better
        # You can adjust the size as needed. CTkFont will use the system's default UI font.
        self.listbox_font = ctk.CTkFont(size=12) # Or try 11 or 13

        ctk.CTkLabel(self, text="Source Folder:").grid(row=0, column=0, padx=10, pady=(10,0), sticky="w")
        self.source_entry = ctk.CTkEntry(self, textvariable=self.source_path, state="readonly", width=400)
        self.source_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.select_source_button = ctk.CTkButton(self, text="Select Source", command=self.select_source_folder)
        self.select_source_button.grid(row=1, column=1, padx=10, pady=5)

        dest_frame = ctk.CTkFrame(self)
        dest_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        dest_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(dest_frame, text="Destination Folders:").grid(row=0, column=0, columnspan=2, padx=5, pady=(5,0), sticky="w")

        # **MODIFIED:** Apply the CTkFont to the standard tkinter Listbox
        # Note: Standard Listbox doesn't directly take CTkFont object, but we can use its properties.
        # We'll use tkfont.Font for compatibility with tkinter.Listbox
        self.listbox_tk_font = tkfont.Font(family=self.listbox_font.cget("family"),
                                           size=self.listbox_font.cget("size"),
                                           weight=self.listbox_font.cget("weight"),
                                           slant=self.listbox_font.cget("slant"))

        self.dest_listbox = Listbox(dest_frame, height=8, width=60, font=self.listbox_tk_font)
        self.dest_listbox.grid(row=1, column=0, padx=(5,0), pady=5, sticky="nsew")
        scrollbar = ctk.CTkScrollbar(dest_frame, command=self.dest_listbox.yview)
        scrollbar.grid(row=1, column=1, padx=(0,5), pady=5, sticky="ns")
        self.dest_listbox.configure(yscrollcommand=scrollbar.set)

        dest_button_frame = ctk.CTkFrame(dest_frame)
        dest_button_frame.grid(row=2, column=0, columnspan=2, pady=5)

        self.add_dest_button = ctk.CTkButton(dest_button_frame, text="Add Destination", command=self.add_destination_folder)
        self.add_dest_button.pack(side=tk.LEFT, padx=5)
        self.remove_dest_button = ctk.CTkButton(dest_button_frame, text="Remove Selected", command=self.remove_destination)
        self.remove_dest_button.pack(side=tk.LEFT, padx=5)

        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        self.save_button = ctk.CTkButton(button_frame, text="Save Task", command=self.save_task)
        self.save_button.pack(side=tk.LEFT, padx=10)
        self.cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side=tk.LEFT, padx=10)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def select_source_folder(self):
        folder_path = filedialog.askdirectory(title="Select Source Folder")
        if folder_path: self.source_path.set(folder_path)

    def add_destination_folder(self):
        folder_path = filedialog.askdirectory(title="Select Destination Folder")
        if folder_path:
            if folder_path == self.source_path.get():
                messagebox.showwarning("Warning", "Destination cannot be the same as the source folder.", parent=self)
                return
            if folder_path in self.current_destinations:
                messagebox.showwarning("Warning", "This destination folder has already been added.", parent=self)
                return
            abs_source = os.path.abspath(self.source_path.get()) if self.source_path.get() else None
            abs_dest = os.path.abspath(folder_path)
            if abs_source:
                 if abs_dest.startswith(abs_source + os.sep):
                      messagebox.showerror("Error", "Destination folder cannot be inside the source folder.", parent=self)
                      return
                 if abs_source.startswith(abs_dest + os.sep):
                      messagebox.showerror("Error", "Source folder cannot be inside a destination folder.", parent=self)
                      return
            self.current_destinations.append(folder_path)
            self.dest_listbox.insert(tk.END, folder_path)

    def remove_destination(self):
        selected_indices = self.dest_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select a destination folder to remove.", parent=self)
            return
        for index in reversed(selected_indices):
            folder_path = self.dest_listbox.get(index)
            self.dest_listbox.delete(index)
            if folder_path in self.current_destinations: self.current_destinations.remove(folder_path)

    def save_task(self):
        source = self.source_path.get()
        destinations = self.current_destinations
        if not source:
            messagebox.showerror("Error", "Please select a source folder.", parent=self)
            return
        if not destinations:
            messagebox.showerror("Error", "Please add at least one destination folder.", parent=self)
            return
        if not os.path.isdir(source):
             messagebox.showerror("Error", f"Source folder does not exist or is not a directory:\n{source}", parent=self)
             return
        for dest in destinations:
             dest_parent = os.path.dirname(dest)
             if not os.path.isdir(dest_parent) and dest_parent != '':
                  messagebox.showerror("Error", f"Parent directory for destination does not exist:\n{dest_parent}", parent=self)
                  return
             if os.path.exists(dest) and not os.path.isdir(dest):
                  messagebox.showerror("Error", f"Destination path exists but is not a directory:\n{dest}", parent=self)
                  return
        self.parent_app.add_task_data(source, destinations)
        self.destroy()

# --- Main Application Class ---
class SyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Real-Time Sync Tool")
        self.geometry("800x650")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sync_tasks = {}
        self.task_frames = {}
        self.selected_task_id = None

        # --- Sidebar Frame ---
        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Sync Tasks", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.add_task_button = ctk.CTkButton(self.sidebar_frame, text="+ Add Task", command=self.add_task_dialog)
        self.add_task_button.grid(row=1, column=0, padx=20, pady=10)

        self.remove_task_button = ctk.CTkButton(self.sidebar_frame, text="- Remove Selected", command=self.remove_selected_task, state="disabled")
        self.remove_task_button.grid(row=2, column=0, padx=20, pady=10)

        self.start_button = ctk.CTkButton(self.sidebar_frame, text="Start Selected", command=self.start_selected_task, state="disabled")
        self.start_button.grid(row=3, column=0, padx=20, pady=10)

        self.stop_button = ctk.CTkButton(self.sidebar_frame, text="Stop Selected", command=self.stop_selected_task, state="disabled")
        self.stop_button.grid(row=4, column=0, padx=20, pady=10)

        self.start_all_button = ctk.CTkButton(self.sidebar_frame, text="Start All Tasks", command=self.start_all_tasks)
        self.start_all_button.grid(row=5, column=0, padx=20, pady=10)

        self.stop_all_button = ctk.CTkButton(self.sidebar_frame, text="Stop All Tasks", command=self.stop_all_tasks_gui)
        self.stop_all_button.grid(row=6, column=0, padx=20, pady=10)

        self.remove_all_tasks_button = ctk.CTkButton(self.sidebar_frame, text="Remove All Tasks", command=self.remove_all_tasks_gui, fg_color="red", hover_color="darkred")
        self.remove_all_tasks_button.grid(row=7, column=0, padx=20, pady=10)


        # --- Main Content Frame (Scrollable) ---
        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=0, label_text="Configured Tasks")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.sync_tasks = self.load_tasks()
        self.update_task_display()
        self.auto_start_all_tasks() # Auto-start tasks after loading and displaying
        self.add_task_dialog_window = None


    def auto_start_all_tasks(self):
        logging.info("Attempting to auto-start all configured tasks...")
        if not self.sync_tasks:
            logging.info("No tasks configured to auto-start.")
            return
        tasks_to_start_ids = [task_id for task_id, info in self.sync_tasks.items() if info.get("status") == "Stopped"]

        if not tasks_to_start_ids:
            logging.info("No tasks are currently stopped to auto-start.")
            return

        for task_id in tasks_to_start_ids:
            if task_id in self.sync_tasks:
                logging.info(f"Auto-starting task {task_id}...")
                self.selected_task_id = task_id
                self.start_selected_task() # This will handle GUI updates and threading
        
        self.after(100, self._deselect_after_auto_start)

    def _deselect_after_auto_start(self):
        self.selected_task_id = None
        self.update_button_states()


    def start_all_tasks(self):
        logging.info("Attempting to start all stopped tasks...")
        started_count = 0
        tasks_to_start_ids = [task_id for task_id, info in self.sync_tasks.items() if info.get("status") == "Stopped"]

        if not tasks_to_start_ids:
            messagebox.showinfo("Start All", "No tasks were in a 'Stopped' state to start.")
            return

        for task_id in tasks_to_start_ids:
            if task_id in self.sync_tasks:
                self.selected_task_id = task_id
                self.start_selected_task()
                started_count +=1
        
        self.after(100, self._deselect_after_auto_start)


    def stop_all_tasks_gui(self):
        logging.info("Attempting to stop all active tasks...")
        stopped_count = 0
        tasks_to_stop_ids = [
            task_id for task_id, info in self.sync_tasks.items()
            if info.get("status", "Stopped") != "Stopped" and not info.get("status", "").startswith("Error")
        ]

        if not tasks_to_stop_ids:
            messagebox.showinfo("Stop All", "No tasks were active to stop.")
            return

        for task_id in tasks_to_stop_ids:
            if task_id in self.sync_tasks:
                self.selected_task_id = task_id
                self.stop_selected_task()
                stopped_count +=1
        
        self.after(100, self._deselect_after_auto_start)


    def remove_all_tasks_gui(self):
        if not self.sync_tasks:
            messagebox.showinfo("Remove All Tasks", "There are no tasks to remove.")
            return
        confirm = messagebox.askyesno("Confirm Remove All",
                                       f"Are you sure you want to remove ALL {len(self.sync_tasks)} configured sync tasks?\n"
                                       "This action cannot be undone.",
                                       icon='warning')
        if confirm:
            logging.info("User confirmed removal of all tasks.")
            if self._internal_stop_all_tasks_logic():
                logging.info("Waiting briefly for tasks to stop before clearing...")
                self.after(3500, self._finalize_remove_all)
            else:
                self._finalize_remove_all()
        else:
            logging.info("User cancelled removal of all tasks.")

    def _finalize_remove_all(self):
        self.sync_tasks.clear()
        self.task_frames.clear()
        self.selected_task_id = None
        logging.info("All tasks have been removed.")
        self.update_task_display()
        self.save_tasks()
        self.update_button_states()
        messagebox.showinfo("Remove All Tasks", "All tasks have been removed.")


    def add_task_dialog(self):
        if self.add_task_dialog_window is None or not self.add_task_dialog_window.winfo_exists():
            self.add_task_dialog_window = AddTaskDialog(self)
            self.add_task_dialog_window.focus()
        else:
            self.add_task_dialog_window.focus()

    def add_task_data(self, source_path, destination_paths):
        task_id = str(uuid.uuid4())[:8]
        abs_source = os.path.abspath(source_path)
        abs_dests = [os.path.abspath(d) for d in destination_paths]

        for existing_id, existing_info in self.sync_tasks.items():
            if existing_info['source'] == abs_source:
                 messagebox.showerror("Error", f"Source folder '{abs_source}' is already configured in task {existing_id}.", parent=self.add_task_dialog_window if self.add_task_dialog_window and self.add_task_dialog_window.winfo_exists() else self)
                 return

        new_task = {
            "source": abs_source,
            "dests": abs_dests,
            "status": "Stopped",
            "thread": None,
            "observer": None,
            "stop_event": threading.Event()
        }
        self.sync_tasks[task_id] = new_task
        logging.info(f"Added new task {task_id}: Source='{abs_source}'")
        self.update_task_display()
        self.save_tasks()

        # **MODIFIED:** Auto-start the newly added task
        logging.info(f"Attempting to auto-start newly added task {task_id}...")
        self.selected_task_id = task_id # Select it
        self.start_selected_task()      # Attempt to start it
        # No need to deselect immediately, next user action or auto_start_all_tasks will handle it.


    def select_task(self, task_id):
        if self.selected_task_id == task_id:
             return
        if self.selected_task_id and self.selected_task_id in self.task_frames:
             if self.task_frames[self.selected_task_id].winfo_exists():
                  self.task_frames[self.selected_task_id].configure(fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        self.selected_task_id = task_id
        if task_id in self.task_frames:
             if self.task_frames[task_id].winfo_exists():
                  self.task_frames[task_id].configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])
        self.update_button_states()

    def update_button_states(self):
        self.remove_all_tasks_button.configure(state="normal" if self.sync_tasks else "disabled")
        self.start_all_button.configure(state="normal" if any(t.get("status") == "Stopped" for t in self.sync_tasks.values()) else "disabled")
        self.stop_all_button.configure(state="normal" if any(t.get("status") != "Stopped" and not t.get("status", "").startswith("Error") for t in self.sync_tasks.values()) else "disabled")

        if self.selected_task_id and self.selected_task_id in self.sync_tasks:
            task_status = self.sync_tasks[self.selected_task_id].get("status", "Unknown")
            is_effectively_running = task_status != "Stopped" and not task_status.startswith("Error")
            self.remove_task_button.configure(state="normal" if not is_effectively_running else "disabled")
            self.start_button.configure(state="normal" if not is_effectively_running else "disabled")
            self.stop_button.configure(state="normal" if is_effectively_running else "disabled")
        else:
            self.remove_task_button.configure(state="disabled")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")

    def remove_selected_task(self):
        task_id_to_remove = self.selected_task_id
        if not task_id_to_remove:
            messagebox.showwarning("Remove Task", "No task selected to remove.")
            return
        if task_id_to_remove not in self.sync_tasks:
             messagebox.showerror("Remove Task Error", f"Selected task ID '{task_id_to_remove}' not found.")
             self.selected_task_id = None
             self.update_task_display()
             self.update_button_states()
             return

        task_info = self.sync_tasks[task_id_to_remove]
        task_status = task_info.get("status", "Stopped")
        if task_status != "Stopped" and not task_status.startswith("Error"):
            messagebox.showwarning("Remove Task", f"Task '{task_id_to_remove}' must be stopped before removal (status: {task_status}).")
            return

        if messagebox.askyesno("Confirm Delete", f"Remove task '{task_id_to_remove}'?\nSource: {task_info.get('source', 'N/A')}", icon='warning'):
            del self.sync_tasks[task_id_to_remove]
            self.selected_task_id = None
            logging.info(f"Removed task {task_id_to_remove}")
            self.update_task_display()
            self.save_tasks()
            self.update_button_states()

    def start_selected_task(self):
        current_selected_id = self.selected_task_id
        if not current_selected_id or current_selected_id not in self.sync_tasks:
            logging.debug("Start selected: No valid task ID selected or task not found.")
            return

        task_id = current_selected_id
        task_info = self.sync_tasks[task_id]
        if task_info.get("status", "Stopped") != "Stopped":
            logging.info(f"Task {task_id} is not stopped (current status: {task_info.get('status', 'Unknown')}). Not starting.")
            return

        task_info["stop_event"].clear()
        self.update_task_status(task_id, "Starting...")
        self.after(50, self._start_worker_thread, task_id)


    def _start_worker_thread(self, task_id):
        if task_id not in self.sync_tasks: return
        task_info = self.sync_tasks[task_id]
        if task_info.get("thread") and task_info["thread"].is_alive():
            logging.warning(f"Worker thread for task {task_id} is already running.")
            return
        thread = threading.Thread(target=self.worker_sync_task, args=(task_id,), name=f"SyncWorker-{task_id}", daemon=True)
        task_info["thread"] = thread
        thread.start()
        self.update_button_states()


    def stop_selected_task(self):
        if not self.selected_task_id or self.selected_task_id not in self.sync_tasks:
            messagebox.showwarning("Stop Task", "No task selected to stop.")
            return

        task_id = self.selected_task_id
        task_info = self.sync_tasks[task_id]

        current_status = task_info.get("status", "Stopped")
        if current_status == "Stopped" or current_status.startswith("Error"):
            logging.info(f"Task {task_id} is already stopped or in an error state.")
            return
        if current_status == "Stopping...":
            logging.info(f"Task {task_id} is already being stopped.")
            return

        logging.info(f"Stopping task {task_id}...")
        self.update_task_status(task_id, "Stopping...")

        if "stop_event" in task_info:
            task_info["stop_event"].set()
        observer = task_info.get("observer")
        if observer and observer.is_alive():
            try:
                observer.stop()
            except Exception as e:
                 logging.error(f"Error requesting observer stop for task {task_id}: {e}")
        self.update_button_states()


    def worker_sync_task(self, task_id):
        task_info = self.sync_tasks.get(task_id)
        if not task_info:
            logging.error(f"[Task {task_id}] Worker: Task data not found.")
            return

        source_path = task_info["source"]
        dest_paths = task_info["dests"]
        stop_event = task_info["stop_event"]
        log_prefix = f"[Task {task_id}] "
        observer_ref = None

        try:
            logging.info(f"{log_prefix}Worker: Starting initial sync from '{source_path}'...")
            self.after(0, self.update_task_status, task_id, "Syncing (Initial)...")
            all_initial_sync_ok = True

            for dest_path in dest_paths:
                if stop_event.is_set():
                    logging.info(f"{log_prefix}Worker: Stop requested during initial sync for {dest_path}.")
                    self.after(0, self.update_task_status, task_id, "Stopped")
                    return
                try:
                    logging.info(f"{log_prefix}Worker: Performing initial sync: '{source_path}' TO '{dest_path}'")
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True, copy_function=shutil.copy2)
                    logging.info(f"{log_prefix}Worker: Initial sync to '{dest_path}' finished.")
                except Exception as e:
                    error_msg = f"Error during initial sync to '{dest_path}': {type(e).__name__} - {e}"
                    logging.error(f"{log_prefix}Worker: {error_msg}")
                    self.after(0, self.update_task_status, task_id, f"Error: Initial sync ({os.path.basename(dest_path)})")
                    all_initial_sync_ok = False
                    return

            if not all_initial_sync_ok: return

            logging.info(f"{log_prefix}Worker: Initial sync complete.")
            self.after(0, self.update_task_status, task_id, "Running")

            event_handler = SyncEventHandler(task_id, source_path, dest_paths, self)
            observer_ref = Observer()
            observer_ref.schedule(event_handler, source_path, recursive=True)
            task_info["observer"] = observer_ref
            observer_ref.start()
            logging.info(f"{log_prefix}Worker: Watchdog observer started.")

            while not stop_event.is_set():
                if not observer_ref.is_alive():
                     logging.warning(f"{log_prefix}Worker: Observer thread unexpectedly stopped.")
                     self.after(0, self.update_task_status, task_id, "Error: Monitor stopped")
                     break
                time.sleep(0.5)

            logging.info(f"{log_prefix}Worker: Loop finished (stop event set or observer died).")

        except Exception as e:
            logging.error(f"{log_prefix}Worker: Unhandled error: {e}")
            self.after(0, self.update_task_status, task_id, f"Error: Worker failed")
        finally:
            if observer_ref and observer_ref.is_alive():
                try:
                    logging.info(f"{log_prefix}Worker: Stopping observer in finally block...")
                    observer_ref.stop()
                    observer_ref.join(timeout=5)
                    if observer_ref.is_alive():
                         logging.warning(f"{log_prefix}Worker: Observer thread did not join within timeout.")
                    else:
                         logging.info(f"{log_prefix}Worker: Observer joined successfully.")
                except Exception as e:
                     logging.error(f"{log_prefix}Worker: Exception joining observer in finally: {e}")

            def final_cleanup_on_main_thread():
                if task_id in self.sync_tasks:
                    current_status = self.sync_tasks[task_id].get("status", "Unknown")
                    if not current_status.startswith("Error"):
                        self.update_task_status(task_id, "Stopped")
                    self._clear_task_runtime_state(task_id)
                logging.info(f"{log_prefix}Worker: Thread finished execution.")

            self.after(0, final_cleanup_on_main_thread)


    def _clear_task_runtime_state(self, task_id):
         if task_id in self.sync_tasks:
              self.sync_tasks[task_id]["thread"] = None
              self.sync_tasks[task_id]["observer"] = None
              self.sync_tasks[task_id]["stop_event"] = threading.Event()
              logging.debug(f"Cleared runtime state for task {task_id}")
         self.update_button_states()


    def update_task_status(self, task_id, status):
        if task_id in self.sync_tasks:
            self.sync_tasks[task_id]["status"] = status
            logging.debug(f"Updating status for task {task_id} to {status}")
            if task_id in self.task_frames and self.task_frames[task_id].winfo_exists():
                label_widget = self.sync_tasks[task_id].get("_status_label_widget")
                if label_widget and label_widget.winfo_exists():
                    label_widget.configure(text=f"Status: {status}")
                else:
                    self.update_task_display()
            else:
                 self.update_task_display()
            self.update_button_states()
        else:
            logging.warning(f"Attempted to update status for non-existent task ID: {task_id}")


    def load_tasks(self):
        tasks = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    tasks_data = json.load(f)
                    if isinstance(tasks_data, dict):
                        tasks = tasks_data
                        for task_id in tasks:
                            tasks[task_id]['status'] = 'Stopped'
                            tasks[task_id]['thread'] = None
                            tasks[task_id]['observer'] = None
                            tasks[task_id]['stop_event'] = threading.Event()
                        logging.info(f"Loaded {len(tasks)} tasks from {CONFIG_FILE}")
                    else:
                        logging.warning(f"Invalid format in {CONFIG_FILE}. Starting fresh.")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading {CONFIG_FILE}: {e}. Starting fresh.")
        else:
             logging.info(f"Config file {CONFIG_FILE} not found. Starting fresh.")
        return tasks

    def save_tasks(self):
        tasks_to_save = {}
        for task_id, task_info in self.sync_tasks.items():
            tasks_to_save[task_id] = {
                "source": task_info["source"],
                "dests": task_info["dests"]
            }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(tasks_to_save, f, indent=4)
            logging.info(f"Saved {len(tasks_to_save)} tasks to {CONFIG_FILE}")
        except IOError as e:
            logging.error(f"Error saving {CONFIG_FILE}: {e}")

    def update_task_display(self):
        scroll_pos = self.main_frame._parent_canvas.yview() if hasattr(self.main_frame, '_parent_canvas') else (0.0, 0.0)
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.task_frames.clear()

        if not self.sync_tasks:
            no_task_label = ctk.CTkLabel(self.main_frame, text="No sync tasks configured yet.", text_color="gray")
            no_task_label.pack(pady=20)
        else:
            sorted_task_ids = sorted(self.sync_tasks.keys())
            for i, task_id in enumerate(sorted_task_ids):
                task_info = self.sync_tasks[task_id]
                status = task_info.get("status", "Unknown")
                source = task_info.get('source', 'N/A')
                dests = task_info.get("dests", [])

                task_frame = ctk.CTkFrame(self.main_frame, border_width=1)
                task_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=(0, 5))
                task_frame.grid_columnconfigure(1, weight=1)
                self.task_frames[task_id] = task_frame

                id_label = ctk.CTkLabel(task_frame, text=f"ID: {task_id}", font=ctk.CTkFont(weight="bold"))
                id_label.grid(row=0, column=0, padx=5, pady=(5,0), sticky="w")

                status_label = ctk.CTkLabel(task_frame, text=f"Status: {status}", anchor="w")
                status_label.grid(row=1, column=0, columnspan=2, padx=5, pady=0, sticky="w")
                task_info["_status_label_widget"] = status_label

                source_label = ctk.CTkLabel(task_frame, text=f"Source: {source}", anchor="w", wraplength=500)
                source_label.grid(row=2, column=0, columnspan=2, padx=5, pady=0, sticky="w")

                dests_text = "Destinations:\n" + "\n".join([f"  - {d}" for d in dests])
                dests_label = ctk.CTkLabel(task_frame, text=dests_text, anchor="w", justify=tk.LEFT, wraplength=500)
                dests_label.grid(row=3, column=0, columnspan=2, padx=5, pady=(0,5), sticky="w")

                task_frame.bind("<Button-1>", lambda event, tid=task_id: self.select_task(tid))
                for widget in task_frame.winfo_children():
                     widget.bind("<Button-1>", lambda event, tid=task_id: self.select_task(tid))

                if task_id == self.selected_task_id:
                     task_frame.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])

        self.main_frame._parent_canvas.yview_moveto(scroll_pos[0])
        self.main_frame.update_idletasks()

    def _internal_stop_all_tasks_logic(self):
         tasks_to_signal_stop = []
         for task_id, task_info in self.sync_tasks.items():
              is_running_or_starting = task_info.get("status", "Stopped") not in ["Stopped", "Error"]
              if is_running_or_starting:
                   tasks_to_signal_stop.append(task_id)
         if not tasks_to_signal_stop:
              logging.info("No tasks were active to signal stop.")
              return False
         for task_id in tasks_to_signal_stop:
              logging.info(f"Signalling stop for task {task_id}")
              task_info = self.sync_tasks[task_id]
              self.update_task_status(task_id, "Stopping...")
              if "stop_event" in task_info:
                  task_info["stop_event"].set()
              observer = task_info.get("observer")
              if observer and observer.is_alive():
                  try:
                      observer.stop()
                  except Exception as e:
                      logging.error(f"Error requesting observer stop for task {task_id} during shutdown: {e}")
         return True

    def on_closing(self):
        logging.info("Window closing...")
        if self._internal_stop_all_tasks_logic():
             logging.info("Waiting briefly for tasks to stop before saving...")
             self.after(3500, self._finalize_close)
        else:
             self._finalize_close()

    def _finalize_close(self):
        logging.info("Finalizing close: saving tasks and destroying window.")
        self.save_tasks()
        self.destroy()


# --- Run the Application ---
if __name__ == "__main__":
    import sys # Ensure sys is imported for console_handler
    setup_logging()

    app = SyncApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
