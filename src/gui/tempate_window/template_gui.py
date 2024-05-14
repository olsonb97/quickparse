import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import yaml
import json
import sys
import os
from src.gui.tempate_window.help_window import show_help

class TemplateEditor(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.show_help = show_help
        self.title("Template Editor")
        self.configure(background="#262626")
        self.center_window(1000, 600)
        self.fonts = {
            'button': ('Nirmala UI', 10),
            'label': ('Nirmala UI', 10),
            'text': ('Consolas', 11)
        }

        self.create_buttons()
        self.create_text_box()
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        try:
            self.iconbitmap(parent.icon_path)
        except:
            pass

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.minsize(550, 300)

    def create_buttons(self):
        button_frame = tk.Frame(self, bg="#262626")
        button_frame.pack(side="top", fill="x")

        load_button = self.create_button(
            button_frame, "Load Template", self.load_template
        )
        save_yaml_button = self.create_button(
            button_frame, "Save as YAML", self.save_yaml_template
        )
        save_json_button = self.create_button(
            button_frame, "Save as JSON", self.save_json_template
        )
        help_button = self.create_button(
            button_frame, "Help", lambda: self.show_help(self)
        )
        load_example_button = self.create_button(
            button_frame, "Load Example", self.load_example
        )

        # Attributes for packing the buttons
        packing_attrs = {
            "side": "left",
            "expand": True,
            "fill": "x",
            "padx": 10,
            "pady": (10,0)
        }

        # Pack the buttons
        for button in [
            load_button, 
            save_yaml_button, 
            save_json_button, 
            help_button, 
            load_example_button
        ]:
            button.pack(**packing_attrs)


    def confirm(self, title, message):
        return bool(messagebox.askyesno(title=title, message=message))

    def create_button(self, parent, text, command):
        button = tk.Button(
            parent, 
            text=text, 
            command=command, 
            bg="black", 
            fg="white", 
            activebackground="black", 
            activeforeground="white", 
            font=self.fonts['button'], 
            border=3
        )
        return button

    def create_text_box(self):
        text_frame = tk.Frame(self, bg="#262626", padx=10, pady=10)
        text_frame.pack(expand=True, fill="both")

        self.text_box = scrolledtext.ScrolledText(
            text_frame, 
            wrap=tk.WORD, 
            bg="black", 
            fg="white", 
            font=self.fonts['text'], 
            insertbackground="white"
        )
        self.text_box.pack(expand=True, fill="both")

    def load_example(self):
        if self.text_box.get("1.0", tk.END).strip():
            if not self.confirm("Confirm", "This will erase everything in the text box. Continue?"):
                return

        # if part of pyinstaller comp
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            resource_path = os.path.join(sys._MEIPASS)
        else:
            resource_path = os.path.join(os.getcwd(), 'resources')

        # Construct the path to the resources folder and the pattern file
        pattern_file_path = os.path.join(resource_path, 'pattern_file.yaml')

        # Load the pattern file content into the text box
        with open(pattern_file_path, "r", encoding='utf-8-sig') as file:
            template_content = file.read()
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", template_content)

    def load_template(self):
        if self.text_box.get("1.0", tk.END).strip():
            if not self.confirm(
                "Confirm", 
                "This will erase everything in the text box. Continue?"
            ):
                return
        file_path = filedialog.askopenfilename(
            filetypes=[("Template Files", "*.yaml;*.yml;*.json")]
        )
        if file_path:
            with open(file_path, "r", encoding='utf-8-sig') as file:
                template_content = file.read()
                self.text_box.delete("1.0", "end")
                self.text_box.insert("1.0", template_content)

    def save_yaml_template(self):
        file_path = filedialog.asksaveasfilename(
            filetypes=[("YAML Files", "*.yaml;*.yml")], 
            defaultextension=".yaml"
        )
        if file_path:
            template_content = self.text_box.get("1.0", "end-1c")
            try:
                yaml.safe_load(template_content)  # Check that YAML is valid
            except yaml.YAMLError as e:
                messagebox.showerror(
                    "Error", 
                    f"Invalid YAML: {e}"
                )
            else:
                with open(file_path, "w", encoding='utf-8') as file:
                    file.write(template_content)
                messagebox.showinfo(
                    "Success", 
                    "Template saved as YAML successfully."
                )

    def save_json_template(self):
        file_path = filedialog.asksaveasfilename(
            filetypes=[("JSON Files", "*.json")], 
            defaultextension=".json"
        )
        if file_path:
            template_content = self.text_box.get("1.0", "end-1c")
            try:
                json.loads(template_content)  # Check that JSON is valid
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Error", 
                    f"Invalid JSON: {e}"
                )
            else:
                with open(file_path, "w", encoding='utf-8') as file:
                    file.write(template_content)
                messagebox.showinfo(
                    "Success",
                    "Template saved as JSON successfully."
                )