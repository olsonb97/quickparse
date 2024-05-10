import tkinter as tk 

def show_help(parent):
    help_window = tk.Toplevel(parent)
    help_window.title("Help")
    help_window.configure(background="#262626")
    help_window.resizable(False, False)

    help_frame = tk.Frame(help_window, bg="#262626")
    help_frame.pack()

    help_text = """\
    Keys: these must occur within the file being parsed. \
Subsequent values that are parsed are determined by which keyword is found \
to have a match within the parsed text. Use "*" as a catch-all keyword name \
that will apply to all files where no other keyword name is located.\
Keys should never be named "Keyword". This name is reserved for parsing.

    Values: Each regex value must have an associated string name, IE \
"Version": "Version (\\S+)". The regex will be what value to \
parse (must contain one pair of "()" to pull something from the text.) \
Names may have lists of regex strings as well. They will parse in order \
until a match is found. Beyond the string name, values may be nested as \
deep as you wish, IE "Common Vals": "Version": "Version (\\S+)".

Example:

    C9200L:
        Version:
        - 'Cisco IOS XE Software, Version (.*)'
        - 'Cisco IOS XE Software Version (\\S+)'
        MAC Address: 'MAC Address\\s+:\\s+(\\S+)'
    '*':
        Version: 'Version (.*)'
    
The above template will do the following to parsed logs \
containing the word 'C9200L':

    - Line in log: "Cisco IOS XE Software Version 17.4"
    - Parsed Info: "Version: 17.4"

    - Line in log: "Cisco Device MAC Address : 12:34:56:78:90:10"
    - Parsed Info: "MAC Address: 12:34:56:78:90:10

For logs without 'C9200L' anywhere in the text, the \
'*' keyword will be used:

    - Line in log: "Version 5"
    - Parsed Info: "Version: 5"\
"""

    help_label = tk.Label(
        help_frame, 
        text=help_text, 
        wraplength=500, 
        justify="left", 
        bg="black", 
        fg="white", 
        font=parent.fonts['label'], 
        relief='groove', 
        padx=8, 
        pady=8,
    )
    help_label.pack(padx=10, pady=10)

    help_window.transient(parent)
    help_window.grab_set()
    try:
        help_window.iconbitmap(parent.parent.icon_path)
    except:
        pass

    # Center the parent on the screen
    help_window.update_idletasks()
    screen_width = help_window.winfo_screenwidth()
    screen_height = help_window.winfo_screenheight()
    size = tuple(
        int(_) for _ in help_window.geometry().split('+')[0].split('x')
    )
    x = (screen_width / 2) - (size[0] / 2)
    y = (screen_height / 2) - (size[1] / 2)
    help_window.geometry("+%d+%d" % (x, y))

    help_window.deiconify()