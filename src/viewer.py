"""Interactive UI for navigating progressive summaries."""

import tkinter as tk
from tkinter import ttk, scrolledtext
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

        # Navigation state (for Phase 2)
        self.current_parent = None
        self.breadcrumb_trail = []

        # Setup window
        filename = document_cache['metadata']['filename']
        self.title(f"Progressive Summarization - {filename}")

        width = config.get('window_width', 800)
        height = config.get('window_height', 600)
        self.geometry(f"{width}x{height}")

        # Create UI components
        self._create_widgets()

        # Initial render
        self.render_level(self.current_level)

    def _create_widgets(self):
        """Create and layout UI components."""
        # Header frame
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        # File label
        filename = self.document_cache['metadata']['filename']
        file_label = ttk.Label(
            header_frame,
            text=f"File: {filename}",
            font=('Arial', 10, 'bold')
        )
        file_label.pack(side=tk.LEFT)

        # Slider frame
        slider_frame = ttk.Frame(self)
        slider_frame.pack(fill=tk.X, padx=10, pady=5)

        # Level label
        self.level_label = ttk.Label(
            slider_frame,
            text=f"Abstraction Level: {self.current_level}/{self.max_level}",
            font=('Arial', 10)
        )
        self.level_label.pack(side=tk.TOP, anchor=tk.W)

        # Slider
        self.slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=self.max_level,
            orient=tk.HORIZONTAL,
            command=self._on_slider_change
        )
        self.slider.set(self.max_level)
        self.slider.pack(side=tk.TOP, fill=tk.X, pady=5)

        # Add level markers below slider
        markers_frame = ttk.Frame(slider_frame)
        markers_frame.pack(side=tk.TOP, fill=tk.X)

        for i in range(self.max_level + 1):
            label_text = "Original" if i == 0 else f"L{i}"
            marker = ttk.Label(markers_frame, text=label_text, font=('Arial', 8))
            marker.pack(side=tk.LEFT, expand=True)

        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Content frame (scrollable)
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create canvas with scrollbar
        self.canvas = tk.Canvas(self.content_frame)
        scrollbar = ttk.Scrollbar(
            self.content_frame,
            orient=tk.VERTICAL,
            command=self.canvas.yview
        )

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel for scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Status bar (for breadcrumbs in Phase 2)
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = ttk.Label(
            self.status_frame,
            text="Ready",
            font=('Arial', 9),
            foreground='gray'
        )
        self.status_label.pack(side=tk.LEFT)

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_slider_change(self, value):
        """Handle slider value change."""
        new_level = int(float(value))
        if new_level != self.current_level:
            self.current_level = new_level
            self.render_level(self.current_level)

    def render_level(self, level: int, parent_id: Optional[str] = None):
        """
        Render chunks at the specified level.

        Args:
            level: Abstraction level to display
            parent_id: Filter by parent (for Phase 2 zoom feature)
        """
        # Clear current content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Update level label
        self.level_label.config(
            text=f"Abstraction Level: {level}/{self.max_level} "
                 f"({'Most Abstract' if level == self.max_level else 'Original Text' if level == 0 else 'Summary'})"
        )

        # Filter chunks by level (and parent if specified)
        filtered_chunks = [
            chunk for chunk in self.chunks
            if chunk['level'] == level and (parent_id is None or chunk.get('parent_id') == parent_id)
        ]

        # Sort by position
        filtered_chunks.sort(key=lambda c: c['position'])

        # Display chunks
        if not filtered_chunks:
            no_content_label = ttk.Label(
                self.scrollable_frame,
                text="No content at this level",
                font=('Arial', 10),
                foreground='gray'
            )
            no_content_label.pack(pady=20)
            return

        font_size = self.config.get('font_size', 12)

        for idx, chunk in enumerate(filtered_chunks):
            # Create frame for each chunk
            chunk_frame = ttk.Frame(self.scrollable_frame, relief=tk.RIDGE, borderwidth=1)
            chunk_frame.pack(fill=tk.X, pady=10, padx=5)

            # Chunk header
            header_text = f"Section {idx + 1}"
            if level == 0:
                header_text = f"Paragraph {idx + 1}"

            header = ttk.Label(
                chunk_frame,
                text=header_text,
                font=('Arial', font_size, 'bold'),
                foreground='#2e5090'
            )
            header.pack(anchor=tk.W, padx=10, pady=(5, 0))

            # Chunk content (scrolled text widget, read-only)
            text_widget = tk.Text(
                chunk_frame,
                wrap=tk.WORD,
                font=('Arial', font_size),
                height=len(chunk['content']) // 80 + 2,  # Approximate height
                relief=tk.FLAT,
                bg='#f8f8f8',
                padx=10,
                pady=10
            )
            text_widget.insert('1.0', chunk['content'])
            text_widget.config(state=tk.DISABLED)  # Make read-only
            text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Placeholder for Phase 2: click-to-zoom
            if chunk['child_ids'] and level > 0:
                zoom_label = ttk.Label(
                    chunk_frame,
                    text="[Click to zoom in - Phase 2]",
                    font=('Arial', 8, 'italic'),
                    foreground='gray'
                )
                zoom_label.pack(anchor=tk.W, padx=10, pady=(0, 5))

        # Update status
        chunk_count = len(filtered_chunks)
        chunk_word = "chunk" if chunk_count == 1 else "chunks"
        self.status_label.config(text=f"Showing {chunk_count} {chunk_word} at level {level}")

    def on_chunk_click(self, chunk_id: str):
        """
        Handle chunk click (Phase 2 feature).

        Args:
            chunk_id: ID of clicked chunk
        """
        # Placeholder for Phase 2 implementation
        pass

    def on_breadcrumb_click(self, index: int):
        """
        Handle breadcrumb click (Phase 2 feature).

        Args:
            index: Index in breadcrumb trail
        """
        # Placeholder for Phase 2 implementation
        pass
