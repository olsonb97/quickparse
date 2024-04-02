from utils.gui import MainWindow
from tkinter import messagebox

if __name__ == "__main__":
    try:
        app = MainWindow()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Error", str(e))