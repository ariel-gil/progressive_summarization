"""Entry point for Progressive Summarization Viewer."""

import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from pathlib import Path
import shutil

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from processor import process_file
from viewer import SummaryViewer


class LoadingDialog(tk.Toplevel):
    """Simple loading dialog."""

    def __init__(self, parent):
        """Initialize loading dialog."""
        super().__init__(parent)
        self.title("Processing...")
        self.geometry("350x120")
        self.resizable(False, False)

        # Center the window
        self.transient(parent)
        self.grab_set()

        # Message
        message = tk.Label(
            self, text="Processing document...\nThis may take a few minutes.",
            font=('Arial', 10), pady=20
        )
        message.pack()

        # Progress bar
        self.progress = ttk.Progressbar(
            self, mode='indeterminate', length=300
        )
        self.progress.pack(pady=10)
        self.progress.start(10)


def show_error(title: str, message: str):
    """Show error dialog."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message)
    root.destroy()


def clear_cache(cache_dir: str = '.summary_cache'):
    """Clear the summary cache directory."""
    cache_path = Path(cache_dir)
    if cache_path.exists():
        try:
            shutil.rmtree(cache_path)
            return True
        except Exception as e:
            print(f"Failed to clear cache: {e}")
            return False
    return True


def main():
    """Main entry point for the application."""
    try:
        # Load configuration
        try:
            config = load_config()
        except FileNotFoundError as e:
            show_error("Configuration Error", str(e))
            return
        except ValueError as e:
            show_error("Configuration Error", str(e))
            return

        # Create temporary root for dialogs
        root = tk.Tk()
        root.withdraw()

        # Ask if user wants to clear cache
        clear = messagebox.askyesno(
            "Clear Cache",
            "Do you want to clear the summary cache?\n\n"
            "Select 'Yes' to regenerate summaries from scratch.\n"
            "Select 'No' to use cached summaries if available.",
            icon='question'
        )

        if clear:
            if clear_cache(config.get('cache_dir', '.summary_cache')):
                messagebox.showinfo("Cache Cleared", "Summary cache has been cleared.")
            else:
                messagebox.showwarning("Cache Clear Failed", "Failed to clear cache, continuing anyway.")

        # Show file picker
        file_path = filedialog.askopenfilename(
            title="Select Markdown File",
            filetypes=[
                ("Markdown Files", "*.md"),
                ("All Files", "*.*")
            ]
        )

        if not file_path:
            root.destroy()
            return

        # Validate file
        if not Path(file_path).exists():
            show_error("File Error", f"File not found: {file_path}")
            root.destroy()
            return

        # Show loading dialog
        loading = LoadingDialog(root)

        # Process file in background thread
        document_cache = None
        error = None
        processing_done = False

        def process_thread():
            nonlocal document_cache, error, processing_done
            try:
                document_cache = process_file(file_path, config)
            except Exception as e:
                error = e
            finally:
                processing_done = True

        def check_processing():
            if processing_done:
                loading.progress.stop()
                loading.destroy()
            else:
                root.after(100, check_processing)

        # Start processing
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()

        # Start polling
        root.after(100, check_processing)

        # Wait for processing to complete
        root.wait_window(loading)

        # Check for errors
        if error:
            show_error(
                "Processing Error",
                f"Failed to process file:\n{str(error)}"
            )
            root.destroy()
            return

        if not document_cache:
            show_error(
                "Processing Error",
                "Failed to process file (no cache generated)"
            )
            root.destroy()
            return

        # Close temporary root
        root.destroy()

        # Launch viewer
        viewer = SummaryViewer(document_cache, config)
        viewer.mainloop()

    except Exception as e:
        show_error("Unexpected Error", f"An unexpected error occurred:\n{str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
