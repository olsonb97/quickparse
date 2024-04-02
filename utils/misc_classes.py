import tkinter as tk

class QuickparserError(Exception):
    def __init__(self, message=""):
        super().__init__(message)

class ParsingError(Exception):
    def __init__(self, message=""):
        super().__init__(message)

# Class to redirect stdout to the text box
class TextRedirector:
    def __init__(self, widget, max_lines=1000, update_interval=20):
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