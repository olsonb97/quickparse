import tkinter as tk

# Class to redirect stdout to the GUI text box
class TextRedirector:
    def __init__(self, widget, max_lines=1000, update_interval=10):
        self.widget = widget
        self.buffer = []
        self.max_lines = max_lines
        self.update_interval = update_interval

    def write(self, string):
        self.buffer.append(string)
        if not hasattr(self, '_scheduled_update'):
            self._scheduled_update = self.widget.after(
                self.update_interval, self.__update_text
            )

    def flush(self):
        pass

    def __update_text(self):
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