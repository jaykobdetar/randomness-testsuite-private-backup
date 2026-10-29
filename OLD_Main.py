"""Compatibility launcher; the historical GUI now uses the validated runner."""
import tkinter as tk
from Main import Main

if __name__ == "__main__":
    root = tk.Tk()
    Main(root)
    root.mainloop()
