"""Interactive UI for navigating progressive summaries with smooth transitions."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import markdown
from tkhtmlview import HTMLScrolledText


class SmoothSlider(ttk.Scale):
    """Custom slider with smooth value changes and callbacks."""

    def __init__(self, parent, on_change_complete=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_change_complete = on_change_complete
        self.last_value = None
        self.after_id = None

        # Bind events for smooth updates
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<B1-Motion>", self._on_drag)

    def _on_drag(self, event):
        """Handle dragging - debounce updates."""
        if self.after_id:
            self.after_cancel(self.after_id)
        self.after_id = self.after(50, self._check_value_change)

    def _on_release(self, event):
        """Handle release - trigger immediate update."""
        if self.after_id:
            self.after_cancel(self.after_id)
        self._check_value_change()

    def _check_value_change(self):
        """Check if value changed and trigger callback."""
        current_value = int(float(self.get()))
        if current_value != self.last_value:
            self.last_value = current_value
            if self.on_change_complete:
                self.on_change_complete(current_value)


class SummaryViewer(tk.Tk):
    """Main window for Progressive Summarization Viewer with smooth transitions."""

    def __init__(self, document_cache: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialize the viewer window.

        Args:
            document_cache: DocumentCache with metadata and levels
            config: Configuration dictionary
        """
        super().__init__()

        self.document_cache = document_cache
        self.app_config = config
        self.levels = document_cache['levels']

        # Calculate max level
        self.max_level = max(level['level'] for level in self.levels)
        self.current_level = self.max_level  # Start at highest abstraction

        # Fade animation state
        self.fade_animation = None

        # Setup window
        filename = document_cache['metadata']['filename']
        self.title(f"Progressive Summarization - {filename}")

        width = config.get('window_width', 1000)
        height = config.get('window_height', 800)
        self.geometry(f"{width}x{height}")
        self.configure(bg='#fafafa')

        # Create UI components
        self._create_widgets()

        # Initial render
        self.render_level(self.current_level, animate=False)

    def _create_widgets(self):
        """Create and layout UI components."""
        # Header section
        header = tk.Frame(self, bg='#ffffff', height=100)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Add subtle shadow effect
        separator = tk.Frame(self, bg='#e0e0e0', height=1)
        separator.pack(fill=tk.X, side=tk.TOP)

        # File info
        info_container = tk.Frame(header, bg='#ffffff')
        info_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        filename = self.document_cache['metadata']['filename'].split('/')[-1]
        file_label = tk.Label(
            info_container,
            text=filename,
            bg='#ffffff',
            fg='#1a1a1a',
            font=('Segoe UI', 16, 'bold')
        )
        file_label.pack(anchor=tk.W)

        # Level indicator
        self.level_label = tk.Label(
            info_container,
            text="",
            bg='#ffffff',
            fg='#666666',
            font=('Segoe UI', 11)
        )
        self.level_label.pack(anchor=tk.W, pady=(5, 0))

        # Slider section
        slider_container = tk.Frame(self, bg='#fafafa')
        slider_container.pack(fill=tk.X, padx=40, pady=(20, 10))

        # Slider label and value
        slider_top = tk.Frame(slider_container, bg='#fafafa')
        slider_top.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            slider_top,
            text="Abstraction Level",
            bg='#fafafa',
            fg='#1a1a1a',
            font=('Segoe UI', 10, 'bold')
        ).pack(side=tk.LEFT)

        self.level_indicator = tk.Label(
            slider_top,
            text="",
            bg='#fafafa',
            fg='#0066cc',
            font=('Segoe UI', 10, 'bold')
        )
        self.level_indicator.pack(side=tk.RIGHT)

        # Custom slider
        self.slider = SmoothSlider(
            slider_container,
            from_=self.max_level,
            to=0,
            orient=tk.HORIZONTAL,
            on_change_complete=self._on_slider_change
        )
        self.slider.set(self.max_level)
        self.slider.pack(fill=tk.X, pady=(0, 10))

        # Level markers
        markers = tk.Frame(slider_container, bg='#fafafa')
        markers.pack(fill=tk.X)

        level_names = []
        for i in range(self.max_level, -1, -1):
            if i == 0:
                level_names.append("Original")
            elif i == self.max_level:
                level_names.append("Ultra")
            elif i == self.max_level - 1:
                level_names.append("Executive")
            else:
                level_names.append(f"L{i}")

        for name in level_names:
            tk.Label(
                markers,
                text=name,
                bg='#fafafa',
                fg='#999999',
                font=('Segoe UI', 8)
            ).pack(side=tk.LEFT, expand=True)

        # Content area with markdown rendering
        content_container = tk.Frame(self, bg='#ffffff')
        content_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=(20, 20))

        # HTML/Markdown viewer
        self.content_viewer = HTMLScrolledText(
            content_container,
            html="",
            background='#ffffff',
            font=('Segoe UI', 11),
            wrap=tk.WORD,
            padx=20,
            pady=20
        )
        self.content_viewer.pack(fill=tk.BOTH, expand=True)

        # Apply custom CSS for better markdown rendering
        self.markdown_css = """
        <style>
            body {
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                line-height: 1.7;
                color: #1a1a1a;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                font-size: 2em;
                font-weight: 700;
                margin-top: 1em;
                margin-bottom: 0.5em;
                color: #0066cc;
            }
            h2 {
                font-size: 1.5em;
                font-weight: 600;
                margin-top: 1.2em;
                margin-bottom: 0.4em;
                color: #1a1a1a;
            }
            h3 {
                font-size: 1.25em;
                font-weight: 600;
                margin-top: 1em;
                margin-bottom: 0.3em;
                color: #333333;
            }
            p {
                margin-bottom: 1em;
            }
            ul, ol {
                margin-bottom: 1em;
                padding-left: 2em;
            }
            li {
                margin-bottom: 0.5em;
            }
            code {
                background-color: #f5f5f5;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 0.9em;
            }
            pre {
                background-color: #f5f5f5;
                padding: 12px;
                border-radius: 4px;
                overflow-x: auto;
                margin-bottom: 1em;
            }
            blockquote {
                border-left: 4px solid #0066cc;
                margin: 1em 0;
                padding-left: 1em;
                color: #666666;
            }
            a {
                color: #0066cc;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
        """

    def _get_level_description(self, level: int) -> str:
        """Get description for abstraction level."""
        if level == 0:
            return "Original document - Full content"
        elif level == self.max_level:
            return "Ultra-compressed - Core essence only"
        elif level == self.max_level - 1:
            return "Executive summary - Main points"
        else:
            return f"Detailed summary - Level {level}"

    def _on_slider_change(self, new_level: int):
        """Handle slider value change."""
        if new_level != self.current_level:
            self.current_level = new_level
            self.render_level(new_level, animate=True)

    def render_level(self, level: int, animate: bool = True):
        """
        Render content at the specified abstraction level.

        Args:
            level: Abstraction level to display
            animate: Whether to animate the transition
        """
        # Find the level data
        level_data = None
        for lvl in self.levels:
            if lvl['level'] == level:
                level_data = lvl
                break

        if not level_data:
            return

        # Update level indicator
        level_desc = self._get_level_description(level)
        self.level_label.config(text=level_desc)

        # Format level indicator badge
        if level == 0:
            badge = "Original"
        else:
            badge = f"Level {level}/{self.max_level}"
        self.level_indicator.config(text=badge)

        # Convert markdown to HTML
        content = level_data['content']
        html_content = markdown.markdown(
            content,
            extensions=['extra', 'codehilite', 'nl2br']
        )

        # Combine CSS and HTML
        full_html = self.markdown_css + html_content

        # Apply fade effect if animating
        if animate:
            self._fade_transition(full_html)
        else:
            self.content_viewer.set_html(full_html)

    def _fade_transition(self, new_html: str):
        """
        Perform a fade transition to new content.

        Args:
            new_html: New HTML content to display
        """
        # Cancel any ongoing animation
        if self.fade_animation:
            self.after_cancel(self.fade_animation)

        # Simple approach: just update content with a brief delay
        # For a real fade, we'd need to manipulate alpha or use a canvas overlay
        self.content_viewer.set_html(new_html)

        # Scroll to top smoothly
        self.content_viewer.yview_moveto(0)
