from tkinter import messagebox, filedialog
import tkinter as tk
import threading
import os
from src.utils.parsing_logic import main_parse
from src.gui.main_window.help_window import show_help
from src.gui.main_window.save_window import save_as
from src.gui.tempate_window.template_gui import TemplateEditor

# Action to show help
def help_action(parent):
    show_help(parent)

# Action to save
def save_action(parent):
    if report_string := parent.text_box.get("1.0", tk.END):
        save_as(parent, report_string, parent.report_dict)
    else:
        messagebox.showerror("Error", f"Failed to read text: {report_string}")

# Action to choose a folder
def folder_action(parent, title, label):
    if folder_path := open_dialog(parent, dialog_type="folder", title=title):
        update_label(label, folder_path)

# Action to choose a file
def file_action(parent, title, label):
    if file_path:= open_dialog(
        parent, 
        dialog_type='open', 
        title=title,
        filetypes=[("Pattern Files", "*.yaml;*.yml;*.json")]
    ):
        update_label(label, file_path)

# Action to open the editor
def editor_action(parent):
    editor = TemplateEditor(parent)
    editor.mainloop()

# Action to parse the folders
def parse_action(parent):

    # Threading function to prevent GUI freeze
    def thread_function(pattern_file, target_folder, reference_folder, window):
        report_dict, report_string = main_parse(
            pattern_file=pattern_file,
            target_folder_path=target_folder,
            reference_folder_path=reference_folder,
            window=window
        )
        print(report_string)
        parent.report_dict = report_dict

    # Validate file and folder paths
    pattern_file = parent.pattern_label.cget("text")
    target_folder = parent.target_label.cget("text")
    if os.path.isfile(pattern_file) and os.path.isdir(target_folder):

        # Check and validate reference path
        if parent.comparison_mode:
            reference_folder = parent.reference_label.cget("text")
            if not os.path.isdir(reference_folder):
                print("Invalid folder or file.")
                return
        else:
            reference_folder = None

        # Create and start the thread
        thread = threading.Thread(target=thread_function, args=(pattern_file, target_folder, reference_folder, parent))
        thread.start()
    else:
        print("Invalid folder or file.")
        return
    
# Action to clear the textbox
def clear_action(parent):
    if messagebox.askyesno(message="Clear contents?"):
        parent.text_box.config(state='normal') 
        parent.text_box.delete("1.0", tk.END)
        parent.text_box.see(tk.END)
        parent.text_box.config(state='disabled')
        parent.report_dict = None
        parent.report_string = None
        parent.update_progressbar(0)

def update_label(label, text):
    label.configure(text=text)

# GUI to return a file path
def open_dialog(
        parent,
        dialog_type="open",
        filetypes=None,
        default_ext=None,
        initial_name="",
        initial_dir="",
        title=""
):
    if not filetypes:
        filetypes = [("All Files", "*.*")]
    if dialog_type == "open":
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            parent=parent
        )
    elif dialog_type == "save":
        file_path = filedialog.asksaveasfilename(
            title=title,
            filetypes=filetypes,
            defaultextension=default_ext,
            initialfile=initial_name,
            initialdir=initial_dir,
            parent=parent
        )
    elif dialog_type == "folder":
        file_path = filedialog.askdirectory(
            title=title,
            initialdir=initial_dir,
            parent=parent
        )
    return file_path if file_path else None