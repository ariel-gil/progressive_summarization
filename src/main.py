"""Entry point for Progressive Summarization Viewer."""

import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from processor import process_file
from viewer import SummaryViewer


class ModernLoadingDialog(tk.Toplevel):
    """Modern loading dialog with better styling."""

    def __init__(self, parent):
        """
        Initialize modern loading dialog.

        Args:
            parent: Parent window
        """
        super().__init__(parent)
        self.title("Processing...")
        self.geometry("400x220")
        self.resizable(False, False)

        # Center the window
        self.transient(parent)
        self.grab_set()

        # Set colors
        self.bg_primary = "#ffffff"
        self.bg_secondary = "#f8f9fa"
        self.accent = "#0d6efd"
        self.config(bg=self.bg_primary)

        # Main frame with padding
        main_frame = tk.Frame(self, bg=self.bg_primary)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        # Title
        title = tk.Label(
            main_frame, text="Processing Document", bg=self.bg_primary,
            fg="#1a1a1a", font=("Segoe UI", 14, "bold")
        )
        title.pack(anchor=tk.W, pady=(0, 10))

        # Subtitle
        subtitle = tk.Label(
            main_frame, text="Generating summaries at multiple abstraction levels...",
            bg=self.bg_primary, fg="#6c757d", font=("Segoe UI", 9)
        )
        subtitle.pack(anchor=tk.W, pady=(0, 20))

        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame, mode='indeterminate', length=340
        )
        self.progress.pack(fill=tk.X, pady=(0, 15))
        self.progress.start(10)

        # Status message
        self.status_label = tk.Label(
            main_frame, text="Starting processing...", bg=self.bg_primary,
            fg="#6c757d", font=("Segoe UI", 9), justify=tk.LEFT
        )
        self.status_label.pack(anchor=tk.W)

        # Cancel button
        button_frame = tk.Frame(main_frame, bg=self.bg_primary)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        self.cancel_button = tk.Button(
            button_frame, text="Cancel", bg=self.bg_secondary,
            fg="#1a1a1a", font=("Segoe UI", 9), padx=15, pady=6,
            relief=tk.FLAT, cursor="hand2"
        )
        self.cancel_button.pack(anchor=tk.E)

    def update_message(self, message: str):
        """Update the loading message."""
        self.status_label.config(text=message)


def show_error(title: str, message: str):
    """
    Show error dialog.

    Args:
        title: Error dialog title
        message: Error message
    """
    root = tk.Tk()
    root.withdraw()  # Hide main window
    messagebox.showerror(title, message)
    root.destroy()


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

        # Create temporary root for file dialog
        root = tk.Tk()
        root.withdraw()  # Hide the root window

        # Show file picker
        file_path = filedialog.askopenfilename(
            title="Select Markdown File",
            filetypes=[
                ("Markdown Files", "*.md"),
                ("All Files", "*.*")
            ]
        )

        if not file_path:
            # User cancelled
            root.destroy()
            return

        # Validate file
        if not Path(file_path).exists():
            show_error("File Error", f"File not found: {file_path}")
            root.destroy()
            return

        # Show loading dialog
        loading = ModernLoadingDialog(root)

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
            """Poll to see if processing is complete."""
            if processing_done:
                loading.progress.stop()  # Stop progress bar animation
                loading.destroy()
            else:
                # Check again in 100ms
                root.after(100, check_processing)

        # Start processing thread
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
