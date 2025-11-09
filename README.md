# Progressive Summarization Viewer

A beautiful web application that generates hierarchical summaries of markdown files with smooth, intuitive navigation between abstraction levels. Based on ideas from Tiago Forte.

## Features

- **Whole-Document Summarization**: Generates 10 levels of abstraction from ultra-compressed to original
- **Smooth Web Interface**: Beautiful, responsive UI with CSS animations and fade transitions
- **Keyboard Navigation**: Use ←/→ arrow keys to zoom in/out smoothly between levels
- **Dark Mode**: Toggle between light and dark themes (Ctrl+D)
- **Smart Caching**: Summaries are cached to avoid reprocessing unchanged files
- **Parallel Processing**: All 10 abstraction levels generated simultaneously for speed
- **Modern Design**: Clean, typography-focused interface with letter-width reading column

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Copy the `.env.template` file to `.env`:

```bash
cp .env.template .env
```

Then edit `.env` and add your OpenRouter API key:

```
OPENROUTER_API_KEY=your-actual-api-key-here
```

Get your API key from: https://openrouter.ai/keys

**Note:** The `.env` file is gitignored and will never be committed to keep your API key secure.

### 3. Run the Application

```bash
python src/main.py
```

The app will automatically open in your default browser at `http://127.0.0.1:5000`

## Usage

1. **Launch**: Run `python src/main.py` (browser opens automatically)
2. **Upload**: Click "Choose Markdown File" and select your .md file
3. **Wait**: Processing takes ~30-60 seconds (generates all 10 levels in parallel)
4. **Navigate**:
   - **Drag Slider**: Smoothly change abstraction level
   - **Arrow Keys**: ← more abstract (compress), → more detail (expand)
   - **Dark Mode**: Click ☀/🌙 button or press Ctrl+D
5. **Abstraction Levels**:
   - **Level 10**: 1-2 sentences (ultra-compressed essence)
   - **Level 9**: 3-5 sentences
   - **Level 8**: 1 paragraph
   - **Level 5**: Executive summary
   - **Level 1-4**: Detailed summaries
   - **Level 0**: Original document

## Configuration

Edit `config.yaml` to customize:

```yaml
# Model settings
model: "google/gemini-2.0-flash-exp:free"  # OpenRouter model
abstraction_levels: 3                      # Number of summary levels

# Processing
chunk_strategy: "paragraph"                # How to split text
group_size: 5                             # Paragraphs per summary

# UI
window_width: 800
window_height: 600
font_size: 12
```

## How It Works

1. **Upload**: User uploads a markdown file via the web interface
2. **Processing**: Entire document is sent to LLM 10 times in parallel with different compression targets
3. **Caching**: Results are cached in `.summary_cache/` for instant reloading
4. **Viewing**: All levels are loaded in browser - switching is instant (client-side only)
5. **Transitions**: Smooth CSS fade animations as you navigate between levels

## Project Structure

```
progressive-summarization/
├── src/
│   ├── main.py              # Entry point (launches web server)
│   ├── web_app.py           # Flask server
│   ├── templates/
│   │   └── index.html       # Web UI (single-page app)
│   ├── processor.py         # Whole-doc summarization logic
│   ├── cache_manager.py     # Cache handling
│   └── config.py            # Configuration
├── .summary_cache/          # Generated summaries (auto-created)
├── config.yaml              # User settings
├── .env                     # API key (gitignored)
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## Technology

- **Backend**: Flask (Python web framework)
- **LLM**: OpenRouter API with Gemini 2.5 Flash
- **Processing**: Async parallel summarization (all 10 levels at once)
- **Frontend**: Vanilla JavaScript + CSS (no frameworks needed)
- **Styling**: CSS custom properties for theming, smooth transitions
- **Caching**: JSON-based file cache for processed documents

## Troubleshooting

**"Config file not found"**
- Make sure `config.yaml` exists in the project root
- Copy and edit the template if needed

**"OpenRouter API key not found"**
- Add your API key to `config.yaml`
- Or set `OPENROUTER_API_KEY` environment variable

**Processing takes too long**
- Reduce `abstraction_levels` in config
- Use a faster model
- Check your internet connection

**Cache issues**
- Delete `.summary_cache/` directory to force regeneration
- Cache is invalidated automatically when file changes

## License

MIT License - See CLAUDE.md for full specification
