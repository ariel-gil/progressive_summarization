"""Interactive UI for navigating progressive summaries."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Any, Optional


class SummaryViewer(tk.Tk):
    """Main window for Progressive Summarization Viewer."""

    def __init__(self, document_cache: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialize the viewer window.

        Args:
            document_cache: DocumentCache with metadata and chunks
            config: Configuration dictionary
        """
        super().__init__()

        self.document_cache = document_cache
        self.config = config
        self.chunks = document_cache['chunks']

        # Calculate max level from chunks
        self.max_level = max(chunk['level'] for chunk in self.chunks)
        self.current_level = self.max_level  # Start at highest abstraction

        # Navigation state
        self.current_parent = None
        self.breadcrumb_trail = []
        self.chunk_id_map = {chunk['id']: chunk for chunk in self.chunks}

        # Setup window
        filename = document_cache['metadata']['filename']
        self.title(f"Progressive Summarization - {filename}")

        width = config.get('window_width', 900)
        height = config.get('window_height', 700)
        self.geometry(f"{width}x{height}")

        # Create UI components
        self._create_widgets()

        # Initial render
        self.render_level(self.current_level)

    def _create_widgets(self):
        """Create and layout UI components."""
        # Top bar with file info
        top_frame = tk.Frame(self, bg='#f0f0f0', height=60)
        top_frame.pack(fill=tk.X, side=tk.TOP)
        top_frame.pack_propagate(False)

        filename = self.document_cache['metadata']['filename']
        file_label = tk.Label(
            top_frame, text=f"File: {filename}",
            bg='#f0f0f0', font=('Arial', 10, 'bold')
        )
        file_label.pack(side=tk.LEFT, padx=15, pady=15)

        # Slider control
        slider_frame = tk.Frame(self)
        slider_frame.pack(fill=tk.X, padx=20, pady=10)

        slider_label = tk.Label(
            slider_frame, text="Abstraction Level:",
            font=('Arial', 9)
        )
        slider_label.pack(side=tk.LEFT, padx=(0, 10))

        # Level indicator
        self.level_indicator = tk.Label(
            slider_frame, text=f"Level {self.max_level}/{self.max_level}",
            font=('Arial', 9, 'bold')
        )
        self.level_indicator.pack(side=tk.RIGHT, padx=10)

        # Slider
        self.slider = ttk.Scale(
            slider_frame, from_=0, to=self.max_level,
            orient=tk.HORIZONTAL,
            command=self._on_slider_change
        )
        self.slider.set(self.max_level)
        self.slider.pack(fill=tk.X, expand=True, padx=(0, 10))

        # Main content area with scrollbar
        content_frame = tk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        # Create canvas and scrollbar
        self.canvas = tk.Canvas(content_frame, bg='white')
        scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg='white')

        # Configure canvas scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Status bar
        status_frame = tk.Frame(self, bg='#f0f0f0', height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame, text="Ready",
            bg='#f0f0f0', font=('Arial', 8)
        )
        self.status_label.pack(side=tk.LEFT, padx=15, pady=5)

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_slider_change(self, value):
        """Handle slider value change."""
        new_level = int(float(value))
        if new_level != self.current_level:
            self.current_level = new_level
            self.current_parent = None
            self.breadcrumb_trail = []
            self.render_level(self.current_level)

    def render_level(self, level: int, parent_id: Optional[str] = None):
        """
        Render chunks at the specified level.

        Args:
            level: Abstraction level to display
            parent_id: Filter by parent (for zoom feature)
        """
        # Clear current content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Filter chunks by level
        filtered_chunks = [
            chunk for chunk in self.chunks
            if chunk['level'] == level and (parent_id is None or chunk.get('parent_id') == parent_id)
        ]

        # Sort by position
        filtered_chunks.sort(key=lambda c: c['position'])

        # Update level indicator
        level_text = "Original" if level == 0 else f"Level {level}/{self.max_level}"
        self.level_indicator.config(text=level_text)

        # Display message if no chunks
        if not filtered_chunks:
            no_content = tk.Label(
                self.scrollable_frame, text="No content at this level",
                bg='white', fg='#999', font=('Arial', 11)
            )
            no_content.pack(pady=40)
            self.status_label.config(text="No chunks to display")
            return

        # Create simple text widgets for each chunk
        for idx, chunk in enumerate(filtered_chunks):
            # Container for each chunk
            chunk_container = tk.Frame(
                self.scrollable_frame,
                bg='white',
                relief=tk.RIDGE,
                borderwidth=1
            )
            chunk_container.pack(fill=tk.X, pady=8, padx=5)

            # Header with chunk number
            header = tk.Frame(chunk_container, bg='#e8e8e8', height=30)
            header.pack(fill=tk.X)
            header.pack_propagate(False)

            chunk_title = "Paragraph" if level == 0 else "Summary"
            title_label = tk.Label(
                header,
                text=f"{chunk_title} {idx + 1}",
                bg='#e8e8e8',
                font=('Arial', 9, 'bold')
            )
            title_label.pack(side=tk.LEFT, padx=10, pady=5)

            # Content text
            text_widget = tk.Text(
                chunk_container,
                wrap=tk.WORD,
                font=('Arial', 10),
                relief=tk.FLAT,
                bg='white',
                padx=10,
                pady=10,
                height=max(3, min(10, len(chunk['content']) // 80 + 1))
            )
            text_widget.insert('1.0', chunk['content'])
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(fill=tk.BOTH, expand=True)

        # Update status
        chunk_count = len(filtered_chunks)
        self.status_label.config(text=f"Showing {chunk_count} chunks at level {level}")

        # Reset scroll to top
        self.canvas.yview_moveto(0)
