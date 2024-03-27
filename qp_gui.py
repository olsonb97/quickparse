from tkinter import filedialog, scrolledtext, messagebox, ttk
import tkinter as tk
import os
import sys
from datetime import datetime
import logging
import threading
from utils.parse_utils import QuickParser

class QuickparseError(Exception):
    def __init__(self, message=""):
        super().__init__(message)

new_pattern_file = r"""
# Define devices (name must appear in the log) and variables:
#
# DeviceName:  # Use device name from logs
#   variableName: 'regexPattern'  # Use one () group in regex
#
# For multiple regex patterns per variable:
#   variableName:
#     - 'pattern1'  # One () group
#     - 'pattern2'  # One () group

---
C1100TGX:
    Version: 'Cisco IOS XE Software, Version (.*)'
C9200L:
    Version: 
    - 'Cisco IOS XE Software, Version (.*)'
    - 'Cisco IOS XE Software Version (.*)'
C93180:
    Version: 'NXOS:\s+version (.*)'
C9336:
    Version: 'NXOS:\s+version (.*)'
N8560:
    Version: 'Software version\s+: (.*)'
FS S3900:
    Version: '(Version\s+\S+\s+Build\s+\d+)'
S5850:
    Version: 'S5850,\s+Version\s+(.*)'
PA-3260:
    Version: 'sw-version:\s+(.*)'
...
"""

# GUI to return a file path
def open_dialog(parent, dialog_type="open", filetypes=[("All Files", "*.*")], default_ext=None, initial_name="", initial_dir="", title=""):
    if dialog_type == "open":
        file_path = filedialog.askopenfilename(title=title, filetypes=filetypes, parent=parent)
    elif dialog_type == "save":
        file_path = filedialog.asksaveasfilename(title=title, filetypes=filetypes, defaultextension=default_ext, initialfile=initial_name, initialdir=initial_dir, parent=parent)
    elif dialog_type == "folder":
        file_path = filedialog.askdirectory(title=title, initialdir=initial_dir, parent=parent)
    return file_path if file_path else None

# Validate the reference folder is valid
def validate_reference_folder(folder_path):
    logging.debug('Validating Reference Folder')
    valid_pattern = False
    valid_logs = False
    for file in os.listdir(folder_path):
        if str(file).endswith(".yaml"):
            valid_pattern = True
        elif str(file).endswith(".log") or file.endswith(".txt"):
            valid_logs = True

    if valid_logs and valid_pattern:
        return None

    if not valid_logs and not valid_pattern:
        error_message = "both pattern file (.yaml) and log files (.log, .txt)"
    elif not valid_logs:
        error_message = "log files (.log, .txt)"
    elif not valid_pattern:
        error_message = "pattern file (.yaml)"
    return f"Reference Folder is not valid: missing {error_message}."

# Get a list of file paths from a folder path
def get_list_of_files(folder_path, exts: tuple):
    logging.debug(f'Building file list for {folder_path}')
    filepaths = []
    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        # Check if it's a file and has the correct extension
        if os.path.isfile(full_path) and file.endswith(exts):
            filepaths.append(full_path)
    return filepaths or None

# Main function for parsing
def main_parse(reference_folder_path, target_folder_path, window):
    logging.debug('Working...')

    # Validate the reference folder
    error_message = validate_reference_folder(reference_folder_path)
    if error_message:
        raise QuickparseError(error_message)

    # Get list of file paths
    target_filepaths = get_list_of_files(target_folder_path, ('.txt', '.log'))
    if not target_filepaths: # Cancel if no parsable files in the target folder
        raise QuickparseError("Cancelled: No files in the target folder can be parsed.")
    reference_filepaths = get_list_of_files(reference_folder_path, ('.txt', '.log'))
    
    # Get the total steps of the progress bar
    num_files_to_scan = len(target_filepaths)
    num_reference_files = len(reference_filepaths)
    total_loading_steps = num_files_to_scan + num_reference_files
    
    # Get other variables
    files_without_devices = [os.path.basename(file) for file in target_filepaths] # As files are parsed, they get removed from here
    total_completed_steps = 0
    scanned_files = 0
    found_devices = set()
    detail_dict = {
        "Reference Folder": {},
        "Scanned Folder": {
            "Matches": {},
            "Deviations": {}
        }
    }

    # Find the pattern file
    pattern_file, = get_list_of_files(reference_folder_path, ('.yaml', '.yml'))
    if not pattern_file: # Cancel if pattern file is None
        raise QuickparseError(f"No pattern file found in Reference Folder: {reference_folder_path}")
    
    # Iterate through reference files
    for reference_file in reference_filepaths:
        
        # Initialize reference file basename and contents
        reference_file_name = os.path.basename(reference_file)
        with open(reference_file, 'r') as file:
            reference_file_contents = file.read()
        
        # Find the device type and OS of the reference file
        device_type = QuickParser.discover(reference_file_contents, pattern_file)
        if not device_type: # Cancel if device discover returns None
            raise QuickparseError(f"No device discovered within reference file: {reference_file_name}. Validate the pattern file's regex.")

        # Create a parser object subject to the device contained in the pattern file
        parser = QuickParser(device_type, pattern_file, log_bool=True)

        # Parse the Reference File
        logging.debug(f"Parsing Reference File: {reference_file_name}")
        parsed_reference_dict = parser.parse(reference_file_contents, collapse=False)

        # Update Progress Bar
        total_completed_steps += 1
        progress = total_completed_steps / total_loading_steps * 100
        window.update_progressbar(progress)

        # Handle any issues
        if not parsed_reference_dict:
            raise QuickparseError(f"Failed to parse reference file: {reference_file_name}. Reference File returned no matches.")
        for key, val in parsed_reference_dict.items(): # Error if reference file fails to parse a variable
            if val == "NOT FOUND":
                raise QuickparseError(f"Failed to parse reference file: {reference_file_name} variable: ({key})")

        # Update detailed dict with the parsed reference file
        device_check = detail_dict["Reference Folder"].get(device_type) # Check if the device has already been found
        if not device_check: # Add ref file to dict if device not already found
            detail_dict["Reference Folder"][device_type] = {reference_file_name: parsed_reference_dict}
        else: # Error if duplicate files for the same device
            duplicate_file, = device_check.keys() # Get dupe file name
            raise QuickparseError(f"Two files for the same device found:\n{reference_file}\n{duplicate_file}")

        # Begin parsing target files against the ref file
        for filepath in target_filepaths.copy(): # Copy in order to simultaneously iterate and remove elements
            base_file = os.path.basename(filepath)
            with open(filepath, 'r') as file:
                file_contents = file.read()
            if device_type in file_contents: # Only parse if the devices match
                if base_file in files_without_devices: # Device is found, so remove the file from the "files_without_devices" list
                    files_without_devices.remove(base_file)
                found_devices.add(device_type)
                logging.debug(f'Parsing File: {base_file}')
                parsed_file_dict = parser.parse(file_contents)
                matches, mismatches = QuickParser.compare(parsed_reference_dict, parsed_file_dict) # Compare the two
                detail_dict["Scanned Folder"]["Matches"].update({base_file: matches})
                detail_dict["Scanned Folder"]["Deviations"].update({base_file: mismatches})
                target_filepaths.remove(filepath) # Remove from original list to shorten future operations
                scanned_files += 1

                # Update Progress Bar
                total_completed_steps += 1
                progress = total_completed_steps / total_loading_steps * 100
                window.update_progressbar(progress)

    # Build the final dictionaries and strings
    detail_dict = QuickParser.collapse(detail_dict)
    brief_dict = {
        "Completion Date": datetime.now().strftime(r'%I:%M %p - %B %d, %Y').lstrip("0"),
        "Devices Found": list(found_devices),
        "Devices Not Found": files_without_devices,
        "Folder (Reference)": reference_folder_path,
        "Folder (Scanned)": target_folder_path,
        "Total Deviations": len(QuickParser.leafify(detail_dict.get("Scanned Folder", {}).get("Deviations", {}))),
        "Total Files Scanned": scanned_files,
        "Total Files Found": num_files_to_scan,
        "Verdict": ("FAIL" if (detail_dict.get("Scanned Folder", {}).get("Deviations") or files_without_devices or (scanned_files != num_files_to_scan)) else "PASS")
    }
    brief_dict = QuickParser.collapse(brief_dict)
    detail_string = QuickParser.serialize(detail_dict, 'yaml')
    brief_string = QuickParser.serialize(brief_dict, 'yaml')
    final_string = "Detailed Report:\n\n" + detail_string + "\n" + ("-"* 100) + "\n\nBrief Report:\n\n" + brief_string + "\n" + ("-"* 100)

    # Ensure Progress Bar finishes
    window.update_progressbar(100)

    # Display final_string
    print("Finished")
    print("\n" + "-" * 100 + "\n")
    print(final_string)

# Class to redirect stdout to the text box
class TextRedirector:
    def __init__(self, widget, max_lines=1000, update_interval=10):
        self.widget = widget
        self.buffer = []
        self.max_lines = max_lines
        self.update_interval = update_interval  # Milliseconds

    def write(self, string):
        self.buffer.append(string)
        if not hasattr(self, '_scheduled_update'):
            self._scheduled_update = self.widget.after(self.update_interval, self._update_text)

    def flush(self):
        pass

    def _update_text(self):
        text_to_insert = ''.join(self.buffer)
        self.widget.config(state='normal')
        self.widget.insert(tk.END, text_to_insert)
        self.widget.see(tk.END)  # Auto-scroll to the end
        self.widget.config(state='disabled')

        # Clear the buffer
        self.buffer.clear()

        # Limit the number of lines in the text box
        lines = self.widget.get('1.0', tk.END).splitlines()
        if len(lines) > self.max_lines:
            self.widget.delete('1.0', f'{len(lines)-self.max_lines}.0')

        delattr(self, '_scheduled_update')

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.setup_window()
        self.configure_ui()
        self.create_widgets()
        self.load_icon()

    # Initialize the configuration settings
    def setup_window(self):
        self.withdraw()  # Hide window temporarily
        self.initialize_config()
        self.deiconify()  # Show window

    # Set the GUI elements
    def configure_ui(self):
        self.title("Quickparse")
        self.configure(background="#2e2b2b")
        self.center_window(1200, 650)
        self.fonts = {
            'button': ('Nirmala UI', 9),
            'label': ('Nirmala UI', 8, 'bold'),
            'text': ('Consolas', 10, 'bold')
        }

    # Get the icon file
    def load_icon(self):
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            resource_path = os.path.join(sys._MEIPASS)
        else:
            resource_path = os.path.join(os.getcwd(), 'resources')

        self.icon_path = os.path.join(resource_path, 'quickparse.ico')
        
        try:
            self.iconbitmap(self.icon_path)
        except Exception as e:
            print(f"Failed to load icon: {e}")

    # Allign everything
    def center_window(self, width, height):
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.minsize(900, 500)
        self.maxsize(self.screen_width, self.screen_height)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(1, weight=1)

    # Initialize widgets
    def create_widgets(self):
        self.create_buttons()
        self.create_labels()
        self.create_text_box()
        self.create_progressbar()

    def create_buttons(self):
        self.choose_reference_button = self.create_button("Choose Reference Folder", lambda: self.folder_action("Choose Reference Folder", self.reference_folder_label), 0, 0)
        self.parse_button = self.create_button("Parse", self.parse_action, 0, 2)
        self.settings_button = self.create_button("Settings", self.open_settings_window, 0, 3)
        self.choose_parse_button = self.create_button("Choose Target Folder",lambda: self.folder_action("Choose Parsing Folder", self.parse_folder_label), 1, 0)
        self.save_button = self.create_button("Save", self.save_action, 1, 2)
        self.clear_button = self.create_button("Clear", self.clear_action, 1, 3)

    def create_button(self, text, command, row, col):
        button = tk.Button(self, text=text, command=command, bg="white", fg="black", font=self.fonts['button'])
        button.grid(row=row, column=col, padx=6, pady=6)
        return button

    def create_labels(self):
        self.reference_folder_label = self.create_label(self.default_reference_path, 0, 1)
        self.parse_folder_label = self.create_label("No folder selected", 1, 1)

    def create_label(self, text, row, col):
        label = tk.Label(self, text=text, bg='#2e2b2b', fg='white', font=self.fonts['label'])
        label.grid(row=row, column=col, padx=5, pady=5)
        return label

    def create_text_box(self):
        self.text_box = scrolledtext.ScrolledText(self, wrap=tk.WORD, bg="black", fg="white", font=self.fonts['text'])
        self.text_box.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        self.text_box.config(state='disabled')

        # Redirect output to the text box
        text_redirector = TextRedirector(self.text_box)
        sys.stdout = text_redirector
        sys.stderr = text_redirector

        # Set up logging to redirect to the text box
        text_redirector = TextRedirector(self.text_box)
        logging_handler = logging.StreamHandler(text_redirector)
        logging_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logging.getLogger().addHandler(logging_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        logger = logging.getLogger()
        logger.addHandler(logging_handler)

    def create_progressbar(self):
        self.progressbar = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=280)
        self.progressbar.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

    def update_progressbar(self, value):
        self.progressbar['value'] = value
        self.update_idletasks()

    # Action to choose a folder
    def folder_action(self, title, label):
        folder_path = open_dialog(parent=self, dialog_type="folder", title=title)
        if folder_path:
            self.update_label(label, folder_path)

    # Action to parse the folders
    def parse_action(self):
        reference_folder = self.reference_folder_label.cget("text")
        parse_folder = self.parse_folder_label.cget("text")
        if os.path.isdir(reference_folder) and os.path.isdir(parse_folder):
            parse_thread = threading.Thread(target=main_parse, args=(reference_folder, parse_folder, self))
            parse_thread.start()  # This will run main_parse in a separate thread so GUI doesn't freeze
        else:
            print("Invalid folder selection")
    # Action to save the textbox to a file
    def save_action(self):
        save_path = open_dialog(self, "save", [("Text File", "*.txt")], ".txt", title="Save as", initial_name="Quickparse_Report")
        if save_path:
            text_content = self.text_box.get("1.0", tk.END)
            with open(save_path, 'w') as file:
                file.write(text_content)
            print(f"Report saved to {save_path}")

    # Action to clear the textbox
    def clear_action(self):
        choice = messagebox.askyesno(message="Clear contents?")
        if choice:
            self.text_box.config(state='normal') 
            self.text_box.delete("1.0", tk.END)
            self.text_box.see(tk.END)
            self.text_box.config(state='disabled')
            self.update_progressbar(0)

    def update_label(self, label, text):
        label.configure(text=text)

    # Initialize the window instance's config data
    def initialize_config(self):
        self.config_path = self.get_config_path()
        self.config_file = self.create_config_file(self.config_path)
        self.load_config_data(self.config_file)

    # Find the config folder
    def get_config_path(self):
        app_name = "Quickparse"
        operating_system = os.name
        platform = sys.platform
        if operating_system == 'nt':  # Windows
            config_path = os.path.join(os.environ['APPDATA'], app_name)
        elif operating_system == 'posix':
            if platform == 'darwin':
                config_path = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'YourAppName')
            else:
                config_path = os.path.join(os.path.expanduser('~'), '.config', 'YourAppName')
        else:
            messagebox.showerror("Error", "Unsupported operating system")
            exit()
        os.makedirs(config_path, exist_ok=True)
        return config_path

    # Create a config file
    def create_config_file(self, config_path, new=False):
        config_file = os.path.join(config_path, 'config.yaml')
        if not new and os.path.exists(config_file):
            pass
        else:
            config_data = {
                'default_reference_path': self.config_path
            }
            with open(config_file, 'w') as file:
                QuickParser.dump(config_data, file, 'yaml')
            messagebox.showinfo("Savefile Created", f"Savefile created at\n{str(config_file)}\n\nThis file is used to save your settings.")
        return config_file

    # Load config file into default paths
    def load_config_data(self, config_file):
        config_dict = QuickParser.load(config_file, 'yaml')
        self.default_reference_path = config_dict['default_reference_path']

    # Update config file with new default paths
    def update_config_data(self, default_reference_path):
        config_data = {
            'default_reference_path': default_reference_path,
        }
        with open(self.config_file, 'w') as file:
            QuickParser.dump(config_data, file, 'yaml')

    # Reset the configuration file
    def reset_config(self):
        self.config_file = self.create_config_file(self.config_path, new=True)
        self.load_config_data(self.config_file)

    # Generate a new pattern file
    def generate_pattern_file(self, path):
        okcancel = messagebox.askokcancel(title="Confirm", message=
                                            "Generating a new file is not recommended. Add to an existing one if possible. One folder may only contain one pattern file.")
        if okcancel:
            save_path = open_dialog(parent=self, dialog_type="save", initial_dir=path, initial_name="pattern_file.yaml", filetypes=[("YAML", "*.yaml")], default_ext=".yaml")
            if save_path:
                with open(save_path, 'w') as file:
                    new_regex_file = QuickParser.dump(new_pattern_file, file, 'yaml')
                if new_regex_file:
                    messagebox.showinfo(title="Success", message=f"Successfully saved to\n{new_regex_file}")

    # Action to open a settings window
    def open_settings_window(self):
        settings_window = tk.Toplevel(self)
        settings_window.title("Settings")
        self.configure_settings_window(settings_window)
        self.populate_settings_widgets(settings_window)
        settings_window.grid_rowconfigure(2, weight=1)
        settings_window.grid_columnconfigure(1, weight=1)

    # Set up the settings window
    def configure_settings_window(self, window):
        width = 800
        height = 100
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2
        window.geometry(f'{width}x{height}+{x}+{y}')
        window.minsize(600, 100)
        window.maxsize(1400, 100)
        window.configure(bg="#2e2b2b")
        window.button_frame = tk.Frame(window, bg="#2e2b2b")
        window.button_frame.grid(row=2, column=0, columnspan=2, pady=5)
        try:
            window.iconbitmap(self.icon_path)
        except:
            pass

    # Create the settings window widgets
    def populate_settings_widgets(self, window):
        # Label for displaying the selected default reference folder
        lbl_reference_path = tk.Label(window, text=self.default_reference_path, bg="#2e2b2b", fg="white", font=self.fonts['label'])
        lbl_reference_path.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Button for choosing the default reference folder
        btn_reference_path = tk.Button(window,
                                  text="Choose Default Reference Folder",
                                  font=self.fonts['button'],
                                  command= lambda: self.update_label(lbl_reference_path,
                                                                     open_dialog(window,
                                                                                      "folder",
                                                                                      title="Choose Default Reference Folder")))
        btn_reference_path.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Save and Reset buttons

        self.create_settings_button(window.button_frame, "Save", lambda: self.save_settings(window, lbl_reference_path.cget('text')))
        self.create_settings_button(window.button_frame, "Reset", lambda: self.reset_action(window))
        self.create_settings_button(window.button_frame, "Generate Pattern File", lambda: self.generate_pattern_file(self.default_reference_path))
        self.create_settings_button(window.button_frame, "Help", lambda: self.show_help(window))

    def show_help(self, window):
        help_window = tk.Toplevel(window)
        help_window.withdraw()
        help_window.iconbitmap(self.icon_path)
        help_window.title("Help")
        help_window.resizable(False, False)
        
        # Set the help text
        help_text = """
        This app manages a local config file storing the default reference folder path,
        which should contain reference log files and one pattern file. A new file can 
        be generated in Settings. If no config file exists, the app creates one.

        Save data path: {config_path}
        -------------------------------------------------------------------------------
        Caution: Only alter this path to delete it.
        """.format(config_path=self.config_path)

        help_label = tk.Label(help_window, text=help_text, wraplength=600, justify="left")
        help_label.pack(padx=5, pady=5)

        # Center the window on the screen
        help_window.update_idletasks()
        screen_width = help_window.winfo_screenwidth()
        screen_height = help_window.winfo_screenheight()
        size = tuple(int(_) for _ in help_window.geometry().split('+')[0].split('x'))
        x = (screen_width / 2) - (size[0] / 2)
        y = (screen_height / 2) - (size[1] / 2)
        help_window.geometry("+%d+%d" % (x, y))

        help_window.deiconify()


    # Template for settings button creation
    def create_settings_button(self, frame, text, command):
        button = tk.Button(frame, text=text, command=command, bg="white", fg="black", font=self.fonts['button'])
        button.pack(side="left", padx=10)

    def reset_action(self, window):
        choice = messagebox.askyesno("Confirm", "Reset default reference folder?", parent=window)
        if choice:
            self.reset_config()
            self.update_label(self.reference_folder_label, self.default_reference_path)
            window.destroy()

    # Action to save settings
    def save_settings(self, window, new_reference_path):
        self.default_reference_path = new_reference_path
        self.update_config_data(self.default_reference_path)
        self.update_label(self.reference_folder_label, self.default_reference_path)
        window.destroy()

if __name__ == "__main__":
    try:
        app = MainWindow()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Error", e)
