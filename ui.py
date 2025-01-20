import tkinter as tk
from tkinter import ttk
from tkinter import PhotoImage  
import sv_ttk
from pynput import keyboard
import threading
import pyperclip
import os

from clipthread.server.feign import ClipboardClient
from clipthread.core.models.clipboard import Clipboard


class TableWindow:
    def __init__(self, client: ClipboardClient):
        self.client = client
        self.uuid_to_complete = {}

        # create main windows
        self.root = tk.Tk()
        self.root.title("Clipthread")
        self.root.iconphoto(True, PhotoImage(file = os.path.join(os.path.dirname(__file__), 'book.png')))
        self.root.geometry('300x200+100+100')
        
        # Flag to track window visibility
        self.is_visible = True

        # Apply modern theme
        sv_ttk.set_theme("dark")  # or "light" for light theme
        
        # Configure styles
        self.style = ttk.Style()
        
        # Style for the main frame
        self.style.configure('Main.TFrame', background='#2b2b2b')
        
        # Style for the Treeview
        self.style.configure("Treeview",
                           background="#2b2b2b",
                           foreground="white",
                           fieldbackground="#2b2b2b",
                           rowheight=25)
        
        # Style for Treeview headings
        self.style.configure("Treeview.Heading",
                           background="#404040",
                           foreground="white",
                           relief="flat")
        self.style.map("Treeview.Heading",
                      background=[('active', '#404040')])
        
        # Style for buttons
        self.style.configure("Accent.TButton",
                           padding=10)
        
        # Create main container with padding and styled
        self.container = ttk.Frame(self.root, style='Main.TFrame')
        self.container.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Container and table setup
        self.container = ttk.Frame(self.root)
        self.container.pack(fill='both', expand=True, padx=2, pady=2)
        
        table_frame = ttk.Frame(self.container)
        table_frame.pack(fill='both', expand=True)
        
        self.tree = ttk.Treeview(table_frame, 
                                columns=('Value',),
                                show='headings',
                                selectmode='browse')
        
        # self.tree.heading('UUID', text='UUID')
        self.tree.heading('Value', text='Value')
        
        # self.tree.column('UUID', width=50, stretch=True)
        self.tree.column('Value', width=200, stretch=True)
        
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', 
                                command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Add control buttons
        button_frame = ttk.Frame(self.container)
        button_frame.pack(fill='x', pady=5)
        ttk.Button(
            button_frame,
            text="Clear",
            style="Accent.TButton",
            command=self.clear_data).pack(side='right', padx=5)
        
        self.tree.bind('<ButtonRelease-1>', self.on_click)
        
        # Configure window resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Set up hotkey listener in a separate thread
        self.setup_hotkey()
        self.refresh_data()

        # overwrite the default close behavior to hide the window instead
        self.root.protocol("WM_DELETE_WINDOW", self.toggle_window)

    def toggle_window(self):
        if self.is_visible:
            self.root.withdraw()  # Hide window
        else:
            self.root.deiconify()  # Show window
        self.is_visible = not self.is_visible

    def setup_hotkey(self):
        def on_press(key):
            try:
                # Check for Ctrl + Alt + [
                if key == keyboard.KeyCode.from_char('['):
                    if keyboard.Key.ctrl.value in self.current_keys and keyboard.Key.alt.value in self.current_keys:
                        # Use after() to safely interact with tkinter from another thread
                        self.root.after(0, self.toggle_window)

                # Check for Ctrl + C
                if key == keyboard.KeyCode.from_char('c'):
                    if keyboard.Key.ctrl.value in self.current_keys:
                        # Get the clipboard content
                        clipboard_content = pyperclip.paste()
                        # print(f"Clipboard content: {clipboard_content}")

                        # insert the clipboard content into the database
                        self.client.create_clipboard(text=clipboard_content, pinned=False)
                        self.refresh_data()

            except AttributeError as e:
                print(f"Unknown key: {key}")
                # print stack trace
                import traceback
                traceback.print_exc()


        def on_release(key):
            try:
                if key.value in self.current_keys:
                    self.current_keys.remove(key.value)
            except AttributeError:
                pass

        # Set to keep track of currently pressed keys
        self.current_keys = set()

        def for_canonical(f):
            return lambda k: f(listener.canonical(k))

        def on_press_with_tracking(key):
            try:
                self.current_keys.add(key.value)
            except AttributeError:
                pass
            on_press(key)

        # Start keyboard listener in a separate thread
        listener = keyboard.Listener(
            on_press=for_canonical(on_press_with_tracking),
            on_release=for_canonical(on_release))
        listener.daemon = True
        listener.start()

    def on_click(self, event):
        item = self.tree.selection()[0]
        values = self.tree.item(item)['values']

        # copy the value to the clipboard
        self.client.get_clipboard(values[0])
        pyperclip.copy(self.uuid_to_complete[values[0]])

    def clear_data(self):
        """Clear all rows from the database and refresh the display"""
        self.client.clear_clipboard()
        self.refresh_data()

    def truncate_text(self, text, limit=25):
        """Truncate text if longer than limit and add ellipsis"""
        return (text[:limit] + '...') if len(text) > limit else text

    def refresh_data(self):
        """Refresh the table data from database"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Load data from database, and insert into the table
        rows: list[Clipboard] = self.client.get_all_clipboards()
        for row in rows:
            self.uuid_to_complete[str(row.id)] = row.text
            # self.tree.insert('', 'end', values=(str(row.id), self.truncate_text(row.text)))
            self.tree.insert('', 'end', values=(self.truncate_text(row.text), ))
    
    def run(self):
        self.root.mainloop()


def start_ui():
    import argparse
    from clipthread.server.main import _start_server

    parser = argparse.ArgumentParser(description='ClipThread server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    
    args = parser.parse_args()

    # In a thread, run the clipthread server
    server_thread = threading.Thread(target=_start_server, args=(args.host, args.port))
    server_thread.daemon = True
    server_thread.start()

    # Run the TableWindow
    client = ClipboardClient(host=args.host, port=args.port)
    app = TableWindow(client)
    app.run()


if __name__ == '__main__':
    start_ui()