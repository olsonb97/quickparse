import tkinter as tk
from tkinter import filedialog, messagebox
import json
import xml.dom.minidom
import logging
import dicttoxml
import yaml

# Turn off dicttoxml's default logging
dicttoxml.LOG.setLevel(logging.ERROR)

def save_as(parent, report_string, report_dict):

    # Initialize window
    save_as_window = tk.Toplevel(parent, background="#262626")
    save_as_window.withdraw()
    try:
        save_as_window.iconbitmap(parent.icon_path)
    except AttributeError:
        pass

    # Basic configuration
    save_as_window.title("Save As")
    save_as_window.resizable(False, False)
    save_as_window.transient(parent)
    save_as_window.grab_set()

    # Create button frame
    button_frame = tk.Frame(save_as_window, bg="#262626")
    button_frame.pack(padx=20, pady=20)

    # Uniform properties for each button
    button_properties = {
        'bg': 'black', 
        'fg': 'white', 
        'padx': 5, 
        'pady': 0, 
        'activebackground': 'black', 
        'activeforeground': 'white', 
        'font': ('Nirmala UI', 10), 
        'border': 3
        }
    
    # Available save options
    options = ["YAML", "JSON", "XML", "TEXT"]

    # Comprehension to create each button
    buttons = [
        tk.Button(
            button_frame,
            command=lambda mode=mode: save_action(
                mode,
                save_as_window,
                report_dict,
                report_string
            ),
            text=mode,
            **button_properties
        ) for mode in options
    ]

    # Pack the buttons
    for button in buttons:
        button.pack(side=tk.LEFT, padx=10)

    # Center window
    save_as_window.update_idletasks()
    width = save_as_window.winfo_reqwidth()
    height = save_as_window.winfo_reqheight()
    x = (parent.screen_width - width) // 2
    y = (parent.screen_height - height) // 2
    save_as_window.geometry(f"{width}x{height}+{x}+{y}")

    save_as_window.deiconify()

def save_action(mode, save_window, report_dict, report_string):
    details = {
        "YAML": {
            "filetypes": [("YAML Files", "*.yaml;*.yml")],
            "defaultextension": ".yaml"
        },
        "JSON": {
            "filetypes": [("JSON Files", "*.json")],
            "defaultextension": ".json"
        },
        "XML": {
            "filetypes": [("XML Files", "*.xml")],
            "defaultextension": ".xml"
        },
        "TEXT": {
            "filetypes": [("Text Files", "*.txt"), ("Log Files", "*.log")],
            "defaultextension": ".txt"
        }
    }
    if file_path := filedialog.asksaveasfilename(
        title="Save As", 
        initialfile="Quickparse_Report", 
        **details[mode]
    ):
        if mode == "YAML":
            with open(file_path, 'w', encoding='utf-8') as file:
                yaml.dump(
                    report_dict, file, default_flow_style=False, indent=4
                )
        elif mode == "JSON":
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(
                    report_dict, file, indent=4
                )
        elif mode == "XML":
            with open(file_path, 'w', encoding='utf-8') as file:
                # Convert dictionary to XML
                xml_obj = dicttoxml.dicttoxml(
                    report_dict, custom_root='Report', attr_type=False
                )
                # Convert bytes to a string
                xml_str = xml.dom.minidom.parseString(xml_obj)
                # Prettify
                pretty_xml = xml_str.toprettyxml()
                file.write(pretty_xml)
        elif mode == "TEXT":
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(report_string)
        save_window.destroy()
        messagebox.showinfo("Success", "File saved successfully.")