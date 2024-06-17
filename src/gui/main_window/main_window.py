from tkinter import scrolledtext, ttk
import tkinter as tk
import os
import sys
import logging
from src.gui.other.text_redirector import TextRedirector
import src.gui.main_window.main_window_actions as actions

# Main GUI
class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.report_dict = None
        self.comparison_mode = False
        self.configure_ui()
        self.create_widgets()
        self.load_icon()

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
        # if part of pyinstaller comp
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            resource_path = os.path.join(sys._MEIPASS)
        else:
            resource_path = os.path.join(os.getcwd(), 'resources')

        self.icon_path = os.path.join(resource_path, 'quickparse.ico')
        
        try:
            self.iconbitmap(self.icon_path)
        except Exception:
            pass

    # Align everything
    def center_window(self, width, height):
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.minsize(900, 500)
        self.maxsize(self.screen_width, self.screen_height)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(1, weight=1)

    # Initialize widgets
    def create_widgets(self):
        self.create_buttons()
        self.create_checkboxes()
        self.create_labels()
        self.create_text_box()
        self.create_progressbar()

    # Create buttons for main GUI
    def create_buttons(self):
        self.parse_button = self.create_button(
            "Parse", lambda: actions.parse_action(self), 0, 2, sticky="e"
        )
        self.help_button = self.create_button(
            "Help", lambda: actions.help_action(self), 0, 3, sticky="e"
        )
        self.save_button = self.create_button(
            "Save", lambda: actions.save_action(self), 1, 2, sticky="e"
        )
        self.clear_button = self.create_button(
            "Clear", lambda: actions.clear_action(self), 1, 3, sticky="e"
        )
        self.editor_button = self.create_button(
            "Editor", lambda: actions.editor_action(self), 2, 3, sticky="e"
        )
        self.pattern_button = self.create_button(
            "Choose Pattern File",
            lambda: actions.file_action(
                self, "Choose Pattern File", self.pattern_label
            ), 0, 0, "w"
        )
        self.target_button = self.create_button(
            "Choose Target Folder", 
            lambda: actions.folder_action(
                self, "Choose Target Folder", self.target_label
            ), 1, 0, "w"
        )
        self.reference_button = self.create_button(
            "Choose Reference Folder", 
            lambda: actions.folder_action(
                self, 
                "Choose Reference Folder", 
                self.reference_label
            ), 2, 0, "w"
        ); self.reference_button.grid_remove()  # Initially hidden

        # Assign button groups
        left_buttons = [
            self.reference_button,
            self.target_button,
            self.pattern_button
        ]

        right_buttons = [
            self.help_button,
            self.clear_button,
            self.save_button,
            self.editor_button,
            self.parse_button
        ]

        # Apply custom width to the buttons
        for btn in left_buttons:
            btn.config(width=22)

        for btn in right_buttons:
            btn.config(width=12)

    def create_button(self, text, command, row, col, sticky=""):
        button = tk.Button(
            self, 
            text=text, 
            command=command, 
            bg="black", 
            fg="white", 
            activebackground="black", 
            activeforeground="white", 
            font=self.fonts['button'], 
            border=3
        )
        button.grid(row=row, column=col, padx=6, pady=6, sticky=sticky)
        return button
    
    def create_checkboxes(self):
        self.comparison_box = self.create_checkbox(
            "Comparison", self.comparison_mode, 2, 2
        )

    def create_checkbox(self, text, variable, row, col):
        checkbox_var = tk.BooleanVar()
        checkbox_var.set(variable)
        checkbox = tk.Checkbutton(
            self, 
            text=text, 
            variable=checkbox_var, 
            bg="#262626", 
            fg="white", 
            selectcolor="black", 
            activebackground="#262626", 
            activeforeground="white", 
            font=self.fonts['button'], 
            command=lambda: self.toggle_comparison_mode(
                checkbox_var.get()
            )
        )
        checkbox.grid(row=row, column=col, padx=6, pady=6)
        return checkbox

    def toggle_comparison_mode(self, value):
        if value:
            self.reference_button.grid(row=2, column=0, padx=6, pady=6)
            self.reference_label.grid(row=2, column=1, padx=6, pady=6)
            self.comparison_mode = True
        else:
            self.reference_button.grid_remove()
            self.reference_label.grid_remove()
            self.comparison_mode = False

    def create_labels(self):
        self.pattern_label = self.create_label(
            "No File Selected", 0, 1, 8, 4
        )
        self.target_label = self.create_label(
            "No Folder Selected", 1, 1, 8, 4
        )
        self.reference_label = self.create_label(
            "No folder selected", 2, 1, 8, 4
        ); self.reference_label.grid_remove()  # Initially hidden

    def create_label(self, text, row, col, padx=0, pady=0):
        label = tk.Label(
            self, 
            text=text,
            bg='black', 
            fg='white', 
            font=self.fonts['label'], 
            relief='groove', 
            padx=padx, pady=pady
        )
        label.grid(row=row, column=col, padx=6, pady=6)
        return label

    def create_text_box(self):
        self.text_box = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, bg="black", fg="white", font=self.fonts['text']
        )
        self.text_box.grid(
            row=3, column=0, columnspan=4, padx=5, pady=5, sticky="nsew"
        )
        self.text_box.config(state='disabled')

        # Redirect output to the text box
        text_redirector = TextRedirector(self.text_box)
        sys.stdout = text_redirector
        sys.stderr = text_redirector

        # Hide traceback for simplicity
        sys.tracebacklimit = 0

        # Set up logging to redirect to the text box
        logging_handler = logging.StreamHandler(text_redirector)
        logging_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        logging.getLogger().addHandler(logging_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        logger = logging.getLogger()
        logger.addHandler(logging_handler)

    def create_progressbar(self):
        self.progressbar = ttk.Progressbar(
            self, 
            orient="horizontal", 
            mode="determinate", 
            length=280
        )
        self.progressbar.grid(
            row=4, 
            column=0, 
            columnspan=4, 
            padx=10, 
            pady=10, 
            sticky="ew"
        )

    def update_progressbar(self, value):
        self.progressbar['value'] = value
        self.update_idletasks()