import tkinter as tk

help_text = (
"Quickparse Help:\n\n"
"Usage Instructions:\n"
"- Prepare Logs: Place all log files in a single folder (.txt or .log).\n"
"- Create Pattern File: Create JSON or YAML templates to define patterns.\n"
"- Load Resources: Load your pattern file and log folder through the GUI.\n"
"- Begin Parsing: Initiate parsing and review the generated report.\n"
"- Save Results: Save parsed data as txt, log, yaml, json, or xml.\n\n"
"Comparison Mode:\n"
"- Prepare Logs: Organize reference and target logs in separate folders.\n"
"- Set Mode: Select 'comparison mode' in the GUI.\n"
"- Load Resources: Load both log folders and your pattern file.\n"
"- Start Parsing: Compare the findings against the reference logs.\n\n"
"Pattern Files:\n"
"- Access Template Editor through the GUI for creating or modifying templates.\n"
"- Use '*' as a pattern keyword catch-all to apply rules universally when no \
specific keyword is matched.\n\n"
"Helpful Tips:\n"
"- Ensure pattern files are correctly formatted to avoid parsing errors.\n"
"- Regularly save your work within the template editor to prevent data loss."
)

def show_help(parent):
    help_window = tk.Toplevel(parent, background="#262626")
    help_window.withdraw()  # Hide during configuration

    # Set icon
    try:
        help_window.iconbitmap(parent.icon_path)
    except AttributeError:
        pass

    # Basic configuration
    help_window.title("Help")
    help_window.resizable(False, False)
    help_window.transient(parent)
    help_window.grab_set()
    
    help_label = tk.Label(
        help_window, 
        text=help_text, 
        wraplength=500, 
        justify="left", 
        bg="black", 
        fg="white", 
        font=parent.fonts['label'], 
        relief='groove', 
        padx=10, 
        pady=10
    )
    help_label.pack(padx=10, pady=10)

    help_window.update_idletasks()

    # Get the width and height
    width = help_window.winfo_reqwidth()
    height = help_window.winfo_reqheight()

    # Position at center
    x = (parent.screen_width - width) // 2
    y = (parent.screen_height - height) // 2
    help_window.geometry(f"{width}x{height}+{x}+{y}")

    # Make visible
    help_window.deiconify()
