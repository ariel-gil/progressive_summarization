"""Interactive UI for navigating progressive summaries with modern design."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class Colors:
    """Color scheme for the application."""
    bg_primary = "#ffffff"
    bg_secondary = "#f8f9fa"
    bg_tertiary = "#e9ecef"
    text_primary = "#1a1a1a"
    text_secondary = "#6c757d"
    text_tertiary = "#adb5bd"
    accent_primary = "#0d6efd"
    accent_secondary = "#0dcaf0"
    card_border = "#dee2e6"
    success = "#198754"
    hover = "#e7f1ff"


class ModernButton(tk.Canvas):
    """Custom button with modern styling and hover effects."""

    def __init__(self, parent, text: str, command=None, **kwargs):
        """Initialize modern button."""
        super().__init__(parent, height=32, bg=Colors.bg_primary, highlightthickness=0, **kwargs)
        self.command = command
        self.text = text
        self.is_hovered = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

        self.draw_button()

    def draw_button(self):
        """Draw button with current state."""
        self.delete("all")
        bg = Colors.hover if self.is_hovered else Colors.accent_primary

        self.create_rectangle(
            2, 2, self.winfo_width() - 2, self.winfo_height() - 2,
            fill=bg, outline=bg, tags="button"
        )
        self.create_text(
            self.winfo_width() // 2, self.winfo_height() // 2,
            text=self.text, fill="white", font=("Segoe UI", 9, "bold"),
            tags="text"
        )

    def _on_enter(self, event):
        """Handle mouse enter."""
        self.is_hovered = True
        self.draw_button()

    def _on_leave(self, event):
        """Handle mouse leave."""
        self.is_hovered = False
        self.draw_button()

    def _on_click(self, event):
        """Handle click."""
        if self.command:
            self.command()


class ChunkCard(tk.Frame):
    """Modern card widget for displaying a chunk."""

    def __init__(self, parent, chunk: Dict, index: int, level: int, max_level: int,
                 on_click=None, **kwargs):
        """Initialize chunk card."""
        super().__init__(parent, bg=Colors.bg_primary, **kwargs)
        self.chunk = chunk
        self.on_click = on_click
        self.is_hovered = False

        # Card styling
        self.config(highlightthickness=1, highlightbackground=Colors.card_border)

        # Bind hover effects
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        self._create_widgets(index, level, max_level)

    def _on_enter(self, event):
        """Handle mouse enter."""
        self.is_hovered = True
        self.config(highlightbackground=Colors.accent_primary, highlightthickness=2)

    def _on_leave(self, event):
        """Handle mouse leave."""
        self.is_hovered = False
        self.config(highlightbackground=Colors.card_border, highlightthickness=1)

    def _create_widgets(self, index: int, level: int, max_level: int):
        """Create card widgets."""
        # Header with title and level indicator
        header = tk.Frame(self, bg=Colors.bg_secondary, height=50)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Build title with topic/header info if available
        title_text = f"Section {index + 1}" if level > 0 else f"Paragraph {index + 1}"

        # Add header/topic info if this chunk has it
        if self.chunk.get('header') and level == 0:
            title_text = f"{self.chunk['header']}"
        elif self.chunk.get('header') and level > 0:
            title_text = f"{title_text} • {self.chunk['header']}"

        title = tk.Label(
            header, text=title_text, bg=Colors.bg_secondary,
            fg=Colors.text_primary, font=("Segoe UI", 11, "bold")
        )
        title.pack(side=tk.LEFT, padx=12, pady=8)

        # Level badge
        badge_text = f"Level {level}/{max_level}" if level > 0 else "Original"
        badge = tk.Label(
            header, text=badge_text, bg=Colors.accent_secondary,
            fg="white", font=("Segoe UI", 8), padx=8, pady=2
        )
        badge.pack(side=tk.RIGHT, padx=12, pady=8)

        # Content
        content_frame = tk.Frame(self, bg=Colors.bg_primary)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Text widget
        text_height = min(max(len(self.chunk['content']) // 80 + 1, 3), 8)
        text_widget = tk.Text(
            content_frame, wrap=tk.WORD,
            font=("Segoe UI", 10), height=text_height,
            relief=tk.FLAT, bg=Colors.bg_tertiary,
            fg=Colors.text_primary, padx=10, pady=10,
            borderwidth=0
        )
        text_widget.insert('1.0', self.chunk['content'])
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Footer with interaction hint and depth indicator
        if self.chunk.get('child_ids') and self.on_click:
            footer = tk.Frame(self, bg=Colors.bg_secondary, height=40)
            footer.pack(fill=tk.X, side=tk.BOTTOM)
            footer.pack_propagate(False)

            hint_frame = tk.Frame(footer, bg=Colors.bg_secondary)
            hint_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=8)

            hint = tk.Label(
                hint_frame, text="↙ Click to zoom in", bg=Colors.bg_secondary,
                fg=Colors.accent_primary, font=("Segoe UI", 9, "italic"),
                cursor="hand2"
            )
            hint.pack(side=tk.LEFT)

            # Add depth indicator (how many children this chunk has)
            child_count = len(self.chunk.get('child_ids', []))
            if child_count > 0:
                depth_indicator = tk.Label(
                    footer, text=f"▶ {child_count} sub-item{'s' if child_count > 1 else ''}",
                    bg=Colors.bg_secondary, fg=Colors.text_tertiary,
                    font=("Segoe UI", 8), padx=8
                )
                depth_indicator.pack(side=tk.RIGHT, padx=4)

            # Make card clickable
            for widget in [self, header, title, footer, hint, text_widget]:
                widget.bind("<Button-1>", lambda e: self.on_click() if self.on_click else None)
                widget.config(cursor="hand2" if self.chunk.get('child_ids') else "arrow")


class SummaryViewer(tk.Tk):
    """Main window for Progressive Summarization Viewer with modern design."""

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

        self.geometry("1000x700")
        self.config(bg=Colors.bg_primary)

        # Create UI components
        self._create_widgets()

        # Initial render
        self.render_level(self.current_level)

    def _create_widgets(self):
        """Create and layout UI components."""
        # Top section with file info and controls
        top_section = tk.Frame(self, bg=Colors.bg_secondary, height=80)
        top_section.pack(fill=tk.X, side=tk.TOP)
        top_section.pack_propagate(False)

        # Left side: file info
        info_frame = tk.Frame(top_section, bg=Colors.bg_secondary)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=15)

        filename = self.document_cache['metadata']['filename']
        file_label = tk.Label(
            info_frame, text=f"📄 {filename}", bg=Colors.bg_secondary,
            fg=Colors.text_primary, font=("Segoe UI", 12, "bold")
        )
        file_label.pack(anchor=tk.W)

        self.level_label = tk.Label(
            info_frame, text="", bg=Colors.bg_secondary,
            fg=Colors.text_secondary, font=("Segoe UI", 9)
        )
        self.level_label.pack(anchor=tk.W, pady=(5, 0))

        # Bind keyboard shortcuts
        self.bind('<Left>', lambda e: self._keyboard_navigate(-1))
        self.bind('<Right>', lambda e: self._keyboard_navigate(1))
        self.bind('<Home>', lambda e: self._jump_to_level(0))
        self.bind('<End>', lambda e: self._jump_to_level(self.max_level))
        self.bind('<?>', lambda e: self._show_help())
        self.bind('<h>', lambda e: self._show_help())

        # Slider section with better styling
        slider_frame = tk.Frame(self, bg=Colors.bg_primary)
        slider_frame.pack(fill=tk.X, padx=20, pady=(15, 10))

        slider_label = tk.Label(
            slider_frame, text="Abstraction Level", bg=Colors.bg_primary,
            fg=Colors.text_primary, font=("Segoe UI", 10, "bold")
        )
        slider_label.pack(anchor=tk.W, pady=(0, 8))

        # Slider with custom styling - scaled by 10 for finer control
        self.slider_scale = 10

        # Real-time level display
        slider_info_frame = tk.Frame(slider_frame, bg=Colors.bg_primary)
        slider_info_frame.pack(fill=tk.X, pady=(0, 8))

        self.slider_value_label = tk.Label(
            slider_info_frame, text="", bg=Colors.bg_primary,
            fg=Colors.accent_primary, font=("Segoe UI", 9, "bold")
        )
        self.slider_value_label.pack(side=tk.RIGHT)

        self.slider = ttk.Scale(
            slider_frame, from_=0, to=self.max_level * self.slider_scale,
            orient=tk.HORIZONTAL, command=self._on_slider_change
        )
        self.slider.set(self.max_level * self.slider_scale)
        self.slider.pack(fill=tk.X, pady=(0, 12))

        # Level markers with ticks
        markers_frame = tk.Frame(slider_frame, bg=Colors.bg_primary)
        markers_frame.pack(fill=tk.X)

        # Create tick marks for each level
        tick_frame = tk.Frame(slider_frame, bg=Colors.bg_primary, height=6)
        tick_frame.pack(fill=tk.X, pady=(0, 4))

        for i in range(self.max_level + 1):
            # Calculate position as percentage
            percentage = i / self.max_level if self.max_level > 0 else 0

            # Create small tick mark
            tick = tk.Label(
                tick_frame, text="|", bg=Colors.bg_primary,
                fg=Colors.text_tertiary, font=("Segoe UI", 6)
            )
            tick.place(relx=percentage, anchor=tk.N)

        # Level labels
        for i in range(self.max_level + 1):
            label_text = "Original" if i == 0 else f"L{i}"
            marker = tk.Label(
                markers_frame, text=label_text, bg=Colors.bg_primary,
                fg=Colors.text_tertiary, font=("Segoe UI", 8)
            )
            marker.pack(side=tk.LEFT, expand=True)

        # Breadcrumb trail
        self.breadcrumb_frame = tk.Frame(self, bg=Colors.bg_primary, height=30)
        self.breadcrumb_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.breadcrumb_frame.pack_propagate(False)

        # Content area (scrollable)
        content_outer = tk.Frame(self, bg=Colors.bg_primary)
        content_outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Canvas with scrollbar
        self.canvas = tk.Canvas(
            content_outer, bg=Colors.bg_primary, highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            content_outer, orient=tk.VERTICAL, command=self.canvas.yview
        )

        self.scrollable_frame = tk.Frame(self.canvas, bg=Colors.bg_primary)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel binding
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Status bar
        status_frame = tk.Frame(self, bg=Colors.bg_secondary, height=40)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame, text="Ready", bg=Colors.bg_secondary,
            fg=Colors.text_secondary, font=("Segoe UI", 9), padx=20, pady=10
        )
        self.status_label.pack(anchor=tk.W)

    def _update_breadcrumbs(self):
        """Update breadcrumb trail display."""
        for widget in self.breadcrumb_frame.winfo_children():
            widget.destroy()

        if not self.breadcrumb_trail:
            return

        trail_text = " → ".join(self.breadcrumb_trail + ["Current"])
        breadcrumb = tk.Label(
            self.breadcrumb_frame, text=trail_text, bg=Colors.bg_primary,
            fg=Colors.text_secondary, font=("Segoe UI", 9), wraplength=900
        )
        breadcrumb.pack(anchor=tk.W)

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling with smooth effect."""
        # Smooth scroll by smaller increments
        self.canvas.yview_scroll(int(-1 * (event.delta / 120) * 2), "units")

    def _on_slider_change(self, value):
        """Handle slider value change."""
        # Scale down from the slider's 0-maxlevel*10 range to actual level
        new_level = int(float(value) / self.slider_scale)

        # Update real-time display
        descriptions = ["Detailed", "Summary", "Abstract", "Very Abstract", "Ultra-Concise"]
        desc = descriptions[min(new_level, len(descriptions) - 1)]
        self.slider_value_label.config(text=f"Level {new_level} • {desc}")

        if new_level != self.current_level:
            self.current_level = new_level
            self.current_parent = None
            self.breadcrumb_trail = []
            # Use after() for smooth rendering without blocking
            self.after(0, lambda: self.render_level(self.current_level))

    def _keyboard_navigate(self, direction: int):
        """Navigate between levels with arrow keys."""
        new_level = self.current_level + direction
        if 0 <= new_level <= self.max_level:
            self.current_level = new_level
            self.current_parent = None
            self.breadcrumb_trail = []
            self.slider.set(new_level * self.slider_scale)
            self.render_level(new_level)

    def _jump_to_level(self, level: int):
        """Jump directly to a level (Home/End keys)."""
        if 0 <= level <= self.max_level:
            self.current_level = level
            self.current_parent = None
            self.breadcrumb_trail = []
            self.slider.set(level * self.slider_scale)
            self.render_level(level)
            # Smooth scroll to top when jumping
            self.canvas.yview_moveto(0)

    def _show_help(self):
        """Show keyboard shortcuts help."""
        help_text = """Progressive Summarization Keyboard Shortcuts

Navigation:
  ← → Arrow Keys     Navigate between abstraction levels
  Home              Jump to original text (Level 0)
  End               Jump to most abstract summary
  Scroll            Smooth scroll through content

Interaction:
  Click Cards       Zoom in on a section to explore further
  Breadcrumbs       Click to navigate back up

Tips:
  • Drag the slider for smooth level transitions
  • Use arrow keys for quick navigation
  • Cards show how many sub-items they contain
  • Press 'H' or '?' anytime to see this help
"""

        help_window = tk.Toplevel(self)
        help_window.title("Keyboard Shortcuts")
        help_window.geometry("400x350")
        help_window.config(bg=Colors.bg_primary)

        # Text widget with help content
        help_display = tk.Text(
            help_window, wrap=tk.WORD, font=("Segoe UI", 9),
            bg=Colors.bg_secondary, fg=Colors.text_primary,
            padx=15, pady=15, relief=tk.FLAT, borderwidth=0
        )
        help_display.insert('1.0', help_text)
        help_display.config(state=tk.DISABLED)
        help_display.pack(fill=tk.BOTH, expand=True)

        # Close button
        close_frame = tk.Frame(help_window, bg=Colors.bg_secondary)
        close_frame.pack(fill=tk.X)

        close_btn = tk.Button(
            close_frame, text="Close", command=help_window.destroy,
            bg=Colors.accent_primary, fg="white",
            font=("Segoe UI", 9), padx=15, pady=8,
            relief=tk.FLAT, cursor="hand2"
        )
        close_btn.pack(pady=10)

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

        # Update breadcrumbs
        self._update_breadcrumbs()

        # Filter chunks by level (and parent if specified)
        filtered_chunks = [
            chunk for chunk in self.chunks
            if chunk['level'] == level and (parent_id is None or chunk.get('parent_id') == parent_id)
        ]

        # Sort by position
        filtered_chunks.sort(key=lambda c: c['position'])

        # Update level label
        if level == 0:
            status_text = "Original text - Full paragraphs"
        elif level == self.max_level:
            status_text = f"Most abstract - Complete summary"
        else:
            status_text = f"Summary level {level} of {self.max_level}"

        self.level_label.config(text=status_text)

        # Display chunks
        if not filtered_chunks:
            no_content = tk.Label(
                self.scrollable_frame, text="No content at this level",
                bg=Colors.bg_primary, fg=Colors.text_tertiary,
                font=("Segoe UI", 11)
            )
            no_content.pack(pady=40)
            return

        # Create cards for each chunk
        for idx, chunk in enumerate(filtered_chunks):
            def make_click_handler(chunk_id):
                def handler():
                    self._on_chunk_click(chunk_id)
                return handler

            card = ChunkCard(
                self.scrollable_frame, chunk, idx, level, self.max_level,
                on_click=make_click_handler(chunk['id']) if chunk.get('child_ids') else None
            )
            card.pack(fill=tk.X, pady=10)

        # Update status
        chunk_count = len(filtered_chunks)
        chunk_word = "chunk" if chunk_count == 1 else "chunks"
        self.status_label.config(
            text=f"Showing {chunk_count} {chunk_word} at level {level}"
        )

    def _on_chunk_click(self, chunk_id: str):
        """
        Handle chunk click for zoom-in navigation.

        Args:
            chunk_id: ID of clicked chunk
        """
        chunk = self.chunk_id_map.get(chunk_id)
        if not chunk or not chunk.get('child_ids'):
            return

        # Update breadcrumb trail
        chunk_num = f"Section {chunk['position']}"
        self.breadcrumb_trail.append(chunk_num)

        # Navigate to child level
        self.current_level -= 1
        self.current_parent = chunk_id
        self.slider.set(self.current_level)
        self.render_level(self.current_level, parent_id=chunk_id)

    def on_breadcrumb_click(self, index: int):
        """
        Handle breadcrumb click to navigate back.

        Args:
            index: Index in breadcrumb trail
        """
        self.breadcrumb_trail = self.breadcrumb_trail[:index]
        self.current_level += 1
        self.slider.set(self.current_level)
        self.render_level(self.current_level)
