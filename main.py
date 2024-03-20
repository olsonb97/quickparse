from tkinter import filedialog, scrolledtext, messagebox, ttk, PhotoImage
import tkinter as tk
import os
import sys
from datetime import datetime
from resources.parse_utils import QuickParser

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
    valid_pattern = False
    valid_logs = False
    for file in os.listdir(folder_path):
        if str(file).endswith(".yaml"):
            valid_pattern = True
        elif str(file).endswith(".log") or file.endswith(".txt"):
            valid_logs = True

    if valid_logs and valid_pattern:
        return True

    if not valid_logs and not valid_pattern:
        error_message = "both pattern file (.yaml) and log files (.log, .txt)"
    elif not valid_logs:
        error_message = "log files (.log, .txt)"
    elif not valid_pattern:
        error_message = "pattern file (.yaml)"
    return f"Reference Folder is not valid: missing {error_message}."

# Main function for parsing
def main_parse(reference_folder_path, folder_path, window):

    error_message = validate_reference_folder(reference_folder_path)
    if error_message != True:
        print(error_message)
        return
    
    print("\nWorking...")

    # Get list of file paths
    filepaths = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file)) and (file.endswith('.log') or file.endswith('.txt'))]
    num_files_to_scan = len(filepaths)
    files_without_devices = filepaths.copy()

    # Get the total steps of the progress bar
    num_reference_files = len([file for file in os.listdir(reference_folder_path) if file.endswith(".txt") or file.endswith(".log")])
    total_loading_steps = num_files_to_scan + num_reference_files
    
    # Get other variables
    total_completed_steps = 0
    scanned_files = 0
    errors = []
    found_devices = set()
    detail_dict = {
        "Reference Folder": {},
        "Scanned Folder": {
            "Matches": {},
            "Deviations": {}
        }
    }

    # Cancel if no parsable files in the parse folder
    if not filepaths:
        print("Cancelled: No files in the selected folder can be parsed.")
        return
    
    # Find the pattern file
    pattern_file = None
    for file in os.listdir(reference_folder_path):
        if str(file).endswith(".yaml"):
            pattern_file = os.path.join(reference_folder_path, file)
    if not pattern_file:
        print(f"No pattern file found in Reference Folder: {reference_folder_path}")
        return
    
    # Iterate through reference files
    for reference_file in os.listdir(reference_folder_path):

        # Verify the reference file
        if not reference_file.endswith(".yaml") and not reference_file.endswith(".txt") and reference_file.endswith(".log"):
            print("Reference Folder not valid. Please make sure the Reference Folder only has logs and a pattern file.")
            return
        
        # Initialize reference variables for reference file
        reference_file_path = os.path.join(reference_folder_path, reference_file)
        reference_file_name = os.path.basename(reference_file_path)
        with open(reference_file_path, 'r') as file:
            reference_file_string = file.read()

        # Cancel if reference file is not valid
        if not reference_file_path.endswith('.txt') and not reference_file_path.endswith('.log'):
            continue
        
        # Find the device type and OS of the reference file
        device_type = QuickParser.discover(reference_file_string, pattern_file)
        if not device_type:
            print(f"No device discovered within reference file: {reference_file_name}. Validate the pattern file's regex.")
            return
        
        # Create a parser object for the device
        parser = QuickParser(device_type, pattern_file, log_bool=True)

        # Parse the Reference File
        parser.log('debug', f"Parsing Reference File: {reference_file_name}")
        parsed_reference_dict = parser.parse(reference_file_string, collapse=False)

        # Update Progress Bar
        total_completed_steps += 1
        progress = total_completed_steps / total_loading_steps * 100
        window.update_progressbar(progress)

        # Handle any issues
        if not parsed_reference_dict:
            print(f"Failed to parse reference file: {reference_file_name}. Reference File returned no matches.")
            return
        for key, val in parsed_reference_dict.items(): # Error if reference fails to parse
            if val == "NOT FOUND":
                errors.append(f"Failed to parse reference file: {reference_file_name} variable: ({key})")

        # Add parsed dict to the detailed dict
        detail_dict["Reference Folder"].update({reference_file_name: parsed_reference_dict})

        # Find files that have same device as the reference file
        for filepath in filepaths:
            base_file = os.path.basename(filepath)
            with open(filepath, 'r') as file:
                file_string = file.read()
            if device_type in file_string:
                # Device is found, so remove it from the list
                if filepath in files_without_devices:
                    files_without_devices.remove(filepath)
                found_devices.add(device_type)
                parser.log('debug', f'Parsing File: {base_file}')
                parsed_file_dict = parser.parse(file_string)
                matches, mismatches = QuickParser.compare(parsed_reference_dict, parsed_file_dict) # Compare the two
                detail_dict["Scanned Folder"]["Matches"].update({base_file: matches})
                detail_dict["Scanned Folder"]["Deviations"].update({base_file: mismatches})
                scanned_files += 1

                # Update Progress Bar
                total_completed_steps += 1
                progress = total_completed_steps / total_loading_steps * 100
                window.update_progressbar(progress)

    # Cancel if nothing parses in the folder
    if not QuickParser.leafify(detail_dict["Scanned Folder"]):
        print("Failed to parse any of the files in the scanned folder.")
        return
    
    # Check that the folder was scanned
    detail_dict = QuickParser.collapse(detail_dict)
    if not detail_dict.get("Scanned Folder"):
        print("Nothing in the scanned folder was parsed.")
        return
    
    # Add devices not found to the errors list
    if files_without_devices:
        for file in files_without_devices:
            errors.append(f"Device Not Found: {os.path.basename(file)}")

    # Build the final dictionaries and strings
    brief_dict = {
        "Completion Date": datetime.now().strftime('%I:%M %p - %B %d, %Y').lstrip("0"),
        "Errors": errors,
        "Folder (Reference)": reference_folder_path,
        "Folder (Scanned)": folder_path,
        "Found Devices": list(found_devices),
        "Total Errors": len(errors),
        "Total File Deviations": len(QuickParser.leafify(detail_dict["Scanned Folder"].get("Deviations", {}))),
        "Total File Matches": len(QuickParser.leafify(detail_dict["Scanned Folder"].get("Matches", {}))),
        "Total Files Scanned": scanned_files,
        "Total Files Found": num_files_to_scan,
        "Verdict": ("FAIL" if (detail_dict["Scanned Folder"].get("Deviations") or scanned_files != num_files_to_scan or errors) else "PASS")
    }
    brief_dict = QuickParser.collapse(brief_dict)
    detail_string = QuickParser.serialize({"Detailed Report": detail_dict}, 'yaml')
    brief_string = QuickParser.serialize(brief_dict, 'yaml')
    final_string = detail_string + "\n" + ("-"* 100) + "\n\nBrief Report:\n\n" + brief_string + "\n" + ("-"* 100)

    # Ensure Progress Bar finishes
    window.update_progressbar(100)

    # Display final_string
    print("Finished")
    print("\n" + "-" * 100 + "\n")
    print(final_string)

# Class to redirect stdout to the text box
class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, string):
        self.widget.after(0, self._insert, string)

    def _insert(self, string):
        self.widget.config(state='normal')
        self.widget.insert(tk.END, string)
        self.widget.see(tk.END)  # Auto-scroll to the end
        self.widget.config(state='disabled')

    def flush(self):
        pass

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
        self.title("QuickParser")
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

        ico_path = os.path.join(resource_path, 'quickparse.ico')
        
        try:
            self.iconbitmap(ico_path)
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
        sys.stdout = TextRedirector(self.text_box)
        sys.stderr = TextRedirector(self.text_box)

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
            main_parse(reference_folder, parse_folder, self)
        else:
            print("Invalid folder selection")
    # Action to save the textbox to a file
    def save_action(self):
        save_path = open_dialog(self, "save", [("YAML", "*.yaml")], ".yaml", title="Save as")
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
        app_name = "QuickParser"
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