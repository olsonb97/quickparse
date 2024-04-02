from tkinter import filedialog, scrolledtext, messagebox, ttk
import tkinter as tk
import os
import sys
import logging
import shutil
import threading
from .quickparser import Quickparser
from .main_parse import main_parse

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

# Main GUI
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
        self.configure(background="#262626")
        self.center_window(1200, 650)
        self.fonts = {
            'button': ('Nirmala UI', 10),
            'label': ('Nirmala UI', 10),
            'text': ('Consolas', 10)
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
        button = tk.Button(self, text=text, command=command, bg="black", fg="white", activebackground="black", activeforeground="white", font=self.fonts['button'], border=3)
        button.grid(row=row, column=col, padx=6, pady=6)
        return button

    def create_labels(self):
        self.reference_folder_label = self.create_label(self.default_reference_path, 0, 1)
        self.parse_folder_label = self.create_label("No folder selected", 1, 1)

    def create_label(self, text, row, col):
        label = tk.Label(self, text=text, bg='black', fg='white', font=self.fonts['label'], relief='groove')
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
        sys.tracebacklimit = 0

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

    # GUI to return a file path
    def open_dialog(self, dialog_type="open", filetypes=[("All Files", "*.*")], default_ext=None, initial_name="", initial_dir="", title=""):
        if dialog_type == "open":
            file_path = filedialog.askopenfilename(title=title, filetypes=filetypes, parent=self)
        elif dialog_type == "save":
            file_path = filedialog.asksaveasfilename(title=title, filetypes=filetypes, defaultextension=default_ext, initialfile=initial_name, initialdir=initial_dir, parent=self)
        elif dialog_type == "folder":
            file_path = filedialog.askdirectory(title=title, initialdir=initial_dir, parent=self)
        return file_path if file_path else None

    # Action to choose a folder
    def folder_action(self, title, label):
        if folder_path := self.open_dialog(dialog_type="folder", title=title):
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
        if save_path := self.open_dialog(self, "save", [("Text File", "*.txt")], ".txt", title="Save as", initial_name="Quickparse_Report"):
            text_content = self.text_box.get("1.0", tk.END)
            with open(save_path, 'w') as file:
                file.write(text_content)
            print(f"Report saved to {save_path}")

    # Action to clear the textbox
    def clear_action(self):
        if messagebox.askyesno(message="Clear contents?"):
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
                Quickparser.dump(config_data, file, 'yaml')
            messagebox.showinfo("Savefile Created", f"Savefile created at\n{str(config_file)}\n\nThis file is used to save your settings.")
        return config_file

    # Load config file into default paths
    def load_config_data(self, config_file):
        config_dict = Quickparser.load(config_file, 'yaml')
        self.default_reference_path = config_dict['default_reference_path']

    # Update config file with new default paths
    def update_config_data(self, default_reference_path):
        config_data = {
            'default_reference_path': default_reference_path,
        }
        with open(self.config_file, 'w') as file:
            Quickparser.dump(config_data, file, 'yaml')

    # Reset the configuration file
    def reset_config(self):
        self.config_file = self.create_config_file(self.config_path, new=True)
        self.load_config_data(self.config_file)

    # Generate a new pattern file
    def generate_pattern_file(self, path):
        if messagebox.askokcancel(title="Confirm", message=
                                            "Generating a new file is not recommended. Add to an existing one if possible. One folder may only contain one pattern file."):
            if save_path := self.open_dialog(dialog_type="save", initial_dir=path, initial_name="pattern_file.yaml", filetypes=[("YAML", "*.yaml")], default_ext=".yaml"):
                base_dir = sys.path[0]  # Directory where the script is located
                source_pattern_file = os.path.join(base_dir, 'resources', 'pattern_file.yaml')
                shutil.copy(source_pattern_file, save_path)
                messagebox.showinfo(title="Success", message=f"Pattern file copied successfully to\n{save_path}")

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
        window.configure(bg="black")
        window.button_frame = tk.Frame(window, bg="black")
        window.button_frame.grid(row=2, column=0, columnspan=2, pady=5)
        try:
            window.iconbitmap(self.icon_path)
        except:
            pass

    # Create the settings window widgets
    def populate_settings_widgets(self, window):
        # Label for displaying the selected default reference folder
        lbl_reference_path = tk.Label(window, text=self.default_reference_path, bg="black", fg="white", font=self.fonts['label'])
        lbl_reference_path.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Button for choosing the default reference folder
        btn_reference_path = tk.Button(window,
                                  text="Choose Default Reference Folder",
                                  font=self.fonts['button'],
                                  command= lambda: self.update_label(lbl_reference_path,
                                                                     self.open_dialog(window,
                                                                                      "folder",
                                                                                      title="Choose Default Reference Folder")),
                                                                                      bg="black",
                                                                                      fg="white",
                                                                                      activebackground="black",
                                                                                      activeforeground="white",
                                                                                      border=3)
        btn_reference_path.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Save and Reset buttons

        self.create_settings_button(window.button_frame, "Save", lambda: self.save_settings(window, lbl_reference_path.cget('text')))
        self.create_settings_button(window.button_frame, "Reset", lambda: self.reset_action(window))
        self.create_settings_button(window.button_frame, "Generate Pattern File", lambda: self.generate_pattern_file(self.default_reference_path))
        self.create_settings_button(window.button_frame, "Help", lambda: self.show_help(window))

    def show_help(self, window):
        help_window = tk.Toplevel(window, background="black")
        help_window.withdraw()
        try:
            help_window.iconbitmap(self.icon_path)
        except:
            pass
        help_window.title("Help")
        help_window.resizable(False, False)
        
        # Set the help text
        help_text = """
This app manages a local config file storing the default
reference folder path, which should contain reference
log files and one pattern file. If no config file exists,
the app creates one. A new pattern file can be generated
in Settings. It has instructions on how to format it.

Save data:
    {config_path}

*CAUTION: Only alter this path to delete it*
""".format(config_path=self.config_path)

        help_label = tk.Label(help_window, text=help_text, wraplength=300, justify="left", bg="black", fg="white")
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
        button = tk.Button(frame, text=text, command=command, bg="black", fg="white", activebackground="black", activeforeground="white", font=self.fonts['button'], border=3)
        button.pack(side="left", padx=10)

    # Action to reset the config file
    def reset_action(self, window):
        if messagebox.askyesno("Confirm", "Reset default reference folder?", parent=window):
            self.reset_config()
            self.update_label(self.reference_folder_label, self.default_reference_path)
            window.destroy()

    # Action to save settings
    def save_settings(self, window, new_reference_path):
        self.default_reference_path = new_reference_path
        self.update_config_data(self.default_reference_path)
        self.update_label(self.reference_folder_label, self.default_reference_path)
        window.destroy()