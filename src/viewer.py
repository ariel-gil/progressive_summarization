"""Interactive UI for navigating progressive summaries with smooth transitions."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional


class Theme:
    """Color themes for the application."""

    # Light theme
    LIGHT = {
        'bg_primary': '#ffffff',
        'bg_secondary': '#fafafa',
        'bg_header': '#ffffff',
        'text_primary': '#1a1a1a',
        'text_secondary': '#666666',
        'text_tertiary': '#999999',
        'accent': '#0066cc',
        'border': '#e0e0e0',
    }

    # Dark theme
    DARK = {
        'bg_primary': '#1e1e1e',
        'bg_secondary': '#252525',
        'bg_header': '#2d2d2d',
        'text_primary': '#e4e4e4',
        'text_secondary': '#b0b0b0',
        'text_tertiary': '#707070',
        'accent': '#4da6ff',
        'border': '#404040',
    }


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

        # Theme state (start with dark mode)
        self.is_dark_mode = True
        self.current_theme = Theme.DARK

        # Store scroll position for smooth transitions
        self.scroll_position = 0.0

        # Setup window
        filename = document_cache['metadata']['filename']
        self.title(f"Progressive Summarization - {filename}")

        width = config.get('window_width', 1100)
        height = config.get('window_height', 850)
        self.geometry(f"{width}x{height}")
        self.configure(bg=self.current_theme['bg_secondary'])

        # Create UI components
        self._create_widgets()

        # Bind keyboard shortcuts
        self.bind('<Left>', self._on_left_arrow)
        self.bind('<Right>', self._on_right_arrow)
        self.bind('<Control-d>', self._toggle_dark_mode)

        # Initial render
        self.render_level(self.current_level, animate=False)

    def _create_widgets(self):
        """Create and layout UI components."""
        # Header section
        header = tk.Frame(self, bg=self.current_theme['bg_header'], height=100)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Add subtle shadow effect
        separator = tk.Frame(self, bg=self.current_theme['border'], height=1)
        separator.pack(fill=tk.X, side=tk.TOP)

        # File info
        info_container = tk.Frame(header, bg=self.current_theme['bg_header'])
        info_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        # Left side: filename
        left_side = tk.Frame(info_container, bg=self.current_theme['bg_header'])
        left_side.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        filename = self.document_cache['metadata']['filename'].split('/')[-1]
        file_label = tk.Label(
            left_side,
            text=filename,
            bg=self.current_theme['bg_header'],
            fg=self.current_theme['text_primary'],
            font=('Inter', 16, 'bold')
        )
        file_label.pack(anchor=tk.W)

        # Level indicator
        self.level_label = tk.Label(
            left_side,
            text="",
            bg=self.current_theme['bg_header'],
            fg=self.current_theme['text_secondary'],
            font=('Inter', 11)
        )
        self.level_label.pack(anchor=tk.W, pady=(5, 0))

        # Right side: dark mode toggle
        right_side = tk.Frame(info_container, bg=self.current_theme['bg_header'])
        right_side.pack(side=tk.RIGHT)

        self.theme_button = tk.Button(
            right_side,
            text="☀ Light Mode",
            command=self._toggle_dark_mode,
            bg=self.current_theme['bg_secondary'],
            fg=self.current_theme['text_primary'],
            font=('Inter', 9),
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        self.theme_button.pack()

        # Slider section
        slider_container = tk.Frame(self, bg=self.current_theme['bg_secondary'])
        slider_container.pack(fill=tk.X, padx=40, pady=(20, 10))

        # Slider label and value
        slider_top = tk.Frame(slider_container, bg=self.current_theme['bg_secondary'])
        slider_top.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            slider_top,
            text="Abstraction Level  (←/→ or drag slider)",
            bg=self.current_theme['bg_secondary'],
            fg=self.current_theme['text_primary'],
            font=('Inter', 10, 'bold')
        ).pack(side=tk.LEFT)

        self.level_indicator = tk.Label(
            slider_top,
            text="",
            bg=self.current_theme['bg_secondary'],
            fg=self.current_theme['accent'],
            font=('Inter', 10, 'bold')
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
        markers = tk.Frame(slider_container, bg=self.current_theme['bg_secondary'])
        markers.pack(fill=tk.X)

        level_names = []
        for i in range(self.max_level, -1, -1):
            if i == 0:
                level_names.append("Original")
            elif i == self.max_level:
                level_names.append("Ultra")
            elif i == self.max_level - 1:
                level_names.append("Brief")
            else:
                level_names.append(f"L{i}")

        for name in level_names:
            tk.Label(
                markers,
                text=name,
                bg=self.current_theme['bg_secondary'],
                fg=self.current_theme['text_tertiary'],
                font=('Inter', 8)
            ).pack(side=tk.LEFT, expand=True)

        # Content area with markdown rendering
        content_container = tk.Frame(self, bg=self.current_theme['bg_primary'])
        content_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=(20, 20))

        # HTML/Markdown viewer with better styling
        import markdown
        from tkhtmlview import HTMLScrolledText

        self.content_viewer = HTMLScrolledText(
            content_container,
            html="<p>Loading...</p>",
            background=self.current_theme['bg_primary'],
            wrap=tk.WORD,
            padx=30,
            pady=20,
            borderwidth=0,
            highlightthickness=0
        )
        self.content_viewer.pack(fill=tk.BOTH, expand=True)

    def _on_left_arrow(self, event=None):
        """Handle left arrow key - increase abstraction (more compressed)."""
        if self.current_level < self.max_level:
            self.current_level += 1
            self.slider.set(self.current_level)
            self.render_level(self.current_level, animate=True)

    def _on_right_arrow(self, event=None):
        """Handle right arrow key - decrease abstraction (more detail)."""
        if self.current_level > 0:
            self.current_level -= 1
            self.slider.set(self.current_level)
            self.render_level(self.current_level, animate=True)

    def _toggle_dark_mode(self, event=None):
        """Toggle between light and dark mode."""
        self.is_dark_mode = not self.is_dark_mode
        self.current_theme = Theme.DARK if self.is_dark_mode else Theme.LIGHT

        # Update theme button text
        self.theme_button.config(
            text="☀ Light Mode" if self.is_dark_mode else "🌙 Dark Mode"
        )

        # Re-render current level with new theme
        self.render_level(self.current_level, animate=False)

        # Update all widget colors
        self._update_theme()

    def _update_theme(self):
        """Update all widget colors to match current theme."""
        # Update main window
        self.configure(bg=self.current_theme['bg_secondary'])

        # Update header and all frames (we'd need to store references)
        # For now, just re-create widgets or manually update
        # This is a simplified approach - in production you'd want widget references
        for widget in self.winfo_children():
            self._update_widget_theme(widget)

    def _update_widget_theme(self, widget):
        """Recursively update widget theme."""
        try:
            # Update frames
            if isinstance(widget, tk.Frame):
                if 'bg_header' in str(widget.cget('bg')) or widget.cget('bg') in ['#ffffff', '#2d2d2d']:
                    widget.config(bg=self.current_theme['bg_header'])
                elif widget.cget('bg') in ['#fafafa', '#252525']:
                    widget.config(bg=self.current_theme['bg_secondary'])
                elif widget.cget('bg') in ['#e0e0e0', '#404040']:
                    widget.config(bg=self.current_theme['border'])

            # Update labels
            if isinstance(widget, tk.Label):
                bg = widget.cget('bg')
                if bg in ['#ffffff', '#2d2d2d']:
                    widget.config(bg=self.current_theme['bg_header'])
                elif bg in ['#fafafa', '#252525']:
                    widget.config(bg=self.current_theme['bg_secondary'])

                fg = widget.cget('fg')
                if fg in ['#1a1a1a', '#e4e4e4']:
                    widget.config(fg=self.current_theme['text_primary'])
                elif fg in ['#666666', '#b0b0b0']:
                    widget.config(fg=self.current_theme['text_secondary'])
                elif fg in ['#999999', '#707070']:
                    widget.config(fg=self.current_theme['text_tertiary'])
                elif fg in ['#0066cc', '#4da6ff']:
                    widget.config(fg=self.current_theme['accent'])

            # Update buttons
            if isinstance(widget, tk.Button):
                widget.config(
                    bg=self.current_theme['bg_secondary'],
                    fg=self.current_theme['text_primary']
                )

            # Update content viewer
            if hasattr(widget, 'set_html'):
                widget.config(background=self.current_theme['bg_primary'])

            # Recursively update children
            for child in widget.winfo_children():
                self._update_widget_theme(child)
        except:
            pass

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

    def _save_scroll_position(self):
        """Save current scroll position as a percentage."""
        try:
            # Get the vertical scrollbar position (0.0 to 1.0)
            yview = self.content_viewer.yview()
            self.scroll_position = yview[0]  # Top of visible area
        except:
            self.scroll_position = 0.0

    def _restore_scroll_position(self):
        """Restore saved scroll position."""
        try:
            self.content_viewer.yview_moveto(self.scroll_position)
        except:
            pass

    def render_level(self, level: int, animate: bool = True):
        """
        Render content at the specified abstraction level.

        Args:
            level: Abstraction level to display
            animate: Whether to animate the transition
        """
        # Save scroll position before changing content
        if animate:
            self._save_scroll_position()

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

        # Convert markdown to HTML (with clean styling)
        import markdown
        content = level_data['content']
        html_content = markdown.markdown(
            content,
            extensions=['extra', 'nl2br']
        )

        # Wrap in a styled div for better appearance
        # Letter width paper is ~8.5 inches = ~650px at typical DPI
        styled_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', system-ui, sans-serif;
                    line-height: 1.65;
                    color: {self.current_theme['text_primary']};
                    font-size: 11.5pt;
                    max-width: 700px;
                    margin: 0 auto;
                    padding: 30px 60px;
                    background-color: {self.current_theme['bg_primary']};">
            {html_content}
        </div>
        <style>
            h1, h2, h3 {{ color: {self.current_theme['accent']}; }}
            a {{ color: {self.current_theme['accent']}; }}
            code {{ background-color: {self.current_theme['bg_secondary']}; }}
        </style>
        """

        # Update content
        self.content_viewer.set_html(styled_html)

        # Restore scroll position after a brief delay
        if animate:
            self.after(10, self._restore_scroll_position)
        else:
            # First load, scroll to top
            self.content_viewer.yview_moveto(0)

    def _fade_transition(self, new_html: str):
        """
        Perform a fade transition to new content.

        Args:
            new_html: New HTML content to display
        """
        # This method is now unused but kept for potential future enhancements
        pass
