import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional # For LoggerCallback, though it's defined in main

# Attempt to import from main.py.
# If main.py is in the same directory, this should work.
# If this script is run as __main__ and main.py is also __main__,
# this can be tricky. Assuming they are part of the same package or PYTHONPATH is set.
try:
    from main import _execute_full_process, LoggerCallback
except ImportError:
    # Fallback for direct execution or if main is not found initially.
    # This might happen if the script is run directly and Python doesn't know where 'main' is.
    # A more robust solution might involve setting PYTHONPATH or packaging.
    import sys
    import os
    # Add the parent directory to sys.path to find main.py
    # This assumes gui.py and main.py are in the same top-level directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    try:
        from main import _execute_full_process, LoggerCallback
    except ImportError as e:
        messagebox.showerror("Import Error", f"Could not import _execute_full_process from main.py: {e}\nMake sure main.py is in the same directory or accessible via PYTHONPATH.")
        _execute_full_process = None # Ensure it's defined to prevent further NameErrors
        LoggerCallback = Optional[callable] # Define a fallback type


class StoryProcessorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Story Processor GUI")

        # Story URL
        ttk.Label(master, text="Story URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.story_url_entry = ttk.Entry(master, width=50)
        self.story_url_entry.grid(row=0, column=1, padx=5, pady=5)

        # Start Chapter URL
        ttk.Label(master, text="Start Chapter URL:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_chapter_url_entry = ttk.Entry(master, width=50)
        self.start_chapter_url_entry.grid(row=1, column=1, padx=5, pady=5)

        # Chapters per EPUB
        ttk.Label(master, text="Chapters per EPUB:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.chapters_per_epub_entry = ttk.Entry(master, width=10)
        self.chapters_per_epub_entry.insert(0, "50")
        self.chapters_per_epub_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # Author Name
        ttk.Label(master, text="Author Name:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.author_name_entry = ttk.Entry(master, width=50)
        self.author_name_entry.grid(row=3, column=1, padx=5, pady=5)

        # Story Title
        ttk.Label(master, text="Story Title:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.story_title_entry = ttk.Entry(master, width=50)
        self.story_title_entry.grid(row=4, column=1, padx=5, pady=5)

        # Keep Intermediate Files
        self.keep_intermediate_files_var = tk.BooleanVar()
        self.keep_intermediate_files_checkbutton = ttk.Checkbutton(
            master, text="Keep Intermediate Files", variable=self.keep_intermediate_files_var
        )
        self.keep_intermediate_files_checkbutton.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # Run Full Process Button
        self.run_button = ttk.Button(master, text="Run Full Process", command=self.start_processing_thread)
        self.run_button.grid(row=6, column=0, columnspan=2, pady=10)

        # Feedback Text Area
        ttk.Label(master, text="Process Log:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        self.feedback_text = tk.Text(master, height=10, width=60, state=tk.DISABLED)
        self.feedback_text.grid(row=8, column=0, columnspan=2, padx=5, pady=5)

        # Add a scrollbar to the feedback text area
        scrollbar = ttk.Scrollbar(master, command=self.feedback_text.yview)
        scrollbar.grid(row=8, column=2, sticky='nsew')
        self.feedback_text['yscrollcommand'] = scrollbar.set

    def _update_feedback_text(self, message: str):
        """Internal method to update feedback text, called by master.after"""
        self.feedback_text.config(state=tk.NORMAL)
        self.feedback_text.insert(tk.END, message + "\n")
        self.feedback_text.see(tk.END)
        self.feedback_text.config(state=tk.DISABLED)

    def gui_logger_callback(self, message: str, style: Optional[str] = None):
        """ Thread-safe callback to log messages to the GUI's feedback text area.
            Style is ignored for now but kept for compatibility with LoggerCallback type.
        """
        # Use master.after to schedule the update in the main Tkinter thread
        self.master.after(0, lambda: self._update_feedback_text(message))

    def _thread_target_for_processing(self, story_url, start_chapter_url, chapters_per_epub,
                                      author_name, story_title, keep_intermediate):
        """ Target function for the processing thread. Calls _execute_full_process. """
        if not _execute_full_process:
            self.gui_logger_callback("Error: _execute_full_process not imported correctly.", "red")
            messagebox.showerror("Critical Error", "_execute_full_process could not be loaded. Cannot proceed.")
            self.master.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            return

        try:
            self.gui_logger_callback("Process started in a new thread...", "blue")
            success, msg, output_path = _execute_full_process(
                story_url=story_url,
                start_chapter_url=start_chapter_url,
                chapters_per_epub=chapters_per_epub,
                author_name_param=author_name,
                story_title_param=story_title,
                keep_intermediate_files=keep_intermediate,
                logger_callback=self.gui_logger_callback
            )
            if success:
                final_message = f"Process completed successfully!\n{msg}\nOutput: {output_path}"
                self.gui_logger_callback(final_message, "green")
                messagebox.showinfo("Success", final_message)
            else:
                final_message = f"Process failed.\n{msg}"
                self.gui_logger_callback(final_message, "red")
                messagebox.showerror("Error", final_message)
        except Exception as e:
            error_msg = f"An unexpected error occurred in the processing thread: {e}\n{traceback.format_exc()}"
            self.gui_logger_callback(error_msg, "red")
            messagebox.showerror("Thread Error", error_msg)
        finally:
            # Re-enable the button, ensuring it's done in the main thread
            self.master.after(0, lambda: self.run_button.config(state=tk.NORMAL))

    def start_processing_thread(self):
        """ Validates inputs and starts the background processing thread. """
        self.run_button.config(state=tk.DISABLED)
        
        # Clear previous feedback
        self.feedback_text.config(state=tk.NORMAL)
        self.feedback_text.delete('1.0', tk.END)
        self.feedback_text.config(state=tk.DISABLED)
        self.gui_logger_callback("--- Starting new process ---", "blue")

        story_url = self.story_url_entry.get().strip()
        start_chapter_url = self.start_chapter_url_entry.get().strip() or None # None if empty
        chapters_per_epub_str = self.chapters_per_epub_entry.get().strip()
        author_name = self.author_name_entry.get().strip() or None # None if empty
        story_title = self.story_title_entry.get().strip() or None # None if empty
        keep_intermediate = self.keep_intermediate_files_var.get()

        if not story_url:
            messagebox.showerror("Input Error", "Story URL is required.")
            self.run_button.config(state=tk.NORMAL)
            return

        try:
            chapters_per_epub = int(chapters_per_epub_str)
            if chapters_per_epub < 0:
                raise ValueError("Chapters per EPUB must be non-negative.")
        except ValueError:
            messagebox.showerror("Input Error", "Chapters per EPUB must be a valid non-negative integer.")
            self.run_button.config(state=tk.NORMAL)
            return

        # All checks passed, start the thread
        thread = threading.Thread(
            target=self._thread_target_for_processing,
            args=(story_url, start_chapter_url, chapters_per_epub,
                  author_name, story_title, keep_intermediate)
        )
        thread.daemon = True # Allows main program to exit even if threads are running
        thread.start()


def start_gui_application():
    """Initializes and runs the Tkinter GUI application."""
    import traceback # For _thread_target_for_processing exception formatting
    root = tk.Tk()
    app = StoryProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    # This makes traceback available globally in this script if run directly
    # It's already imported in _thread_target_for_processing for safety.
    import traceback 
    start_gui_application()
