# Progressive Summarization Viewer

A desktop application that generates hierarchical summaries of markdown files and provides an interactive viewer to navigate between abstraction levels.

## Features

- **Bottom-Up Summarization**: Automatically generates multiple levels of abstraction from your markdown documents
- **Interactive Navigation**: Use a slider to smoothly navigate between detail and abstraction
- **Smart Caching**: Summaries are cached to avoid reprocessing unchanged files
- **Parallel Processing**: Efficient batch processing with concurrent API calls
- **Clean UI**: Simple tkinter interface focused on readability

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Edit `config.yaml` and add your OpenRouter API key:

```yaml
openrouter_api_key: "your-key-here"
```

Or set it as an environment variable:

```bash
export OPENROUTER_API_KEY="your-key-here"
```

Get your API key from: https://openrouter.ai/keys

### 3. Run the Application

```bash
python src/main.py
```

## Usage

1. **Launch**: Run `python src/main.py`
2. **Select File**: Choose a markdown file from the file picker
3. **Wait**: Processing may take a few minutes depending on file size
4. **Navigate**: Use the slider to move between abstraction levels:
   - Level 0: Original text (paragraphs)
   - Level 1-N: Progressively more abstract summaries
   - Highest level: Most condensed overview

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

1. **Parsing**: Markdown is split into paragraphs (Level 0)
2. **Grouping**: Paragraphs are grouped into batches (default: 5)
3. **Summarization**: Each batch is summarized via OpenRouter API
4. **Iteration**: Summaries are grouped and summarized again until reaching desired abstraction level
5. **Caching**: Results are cached in `.summary_cache/` for fast reloading

## Project Structure

```
progressive-summarization/
├── src/
│   ├── main.py           # Entry point
│   ├── processor.py      # Summarization logic
│   ├── viewer.py         # UI components
│   ├── cache_manager.py  # Cache handling
│   └── config.py         # Configuration
├── .summary_cache/       # Generated summaries (auto-created)
├── config.yaml           # User settings
├── requirements.txt      # Dependencies
└── README.md            # This file
```

## Roadmap

**Phase 1 (MVP)** ✅
- Configuration loading
- Basic caching
- Markdown parsing + bottom-up summarization
- Basic UI with slider navigation

**Phase 2 (Enhancements)** 🚧
- Click-to-zoom navigation
- Breadcrumb trail
- Better error handling
- Progress indicators during processing

**Phase 3 (Future)** 📋
- File watching for auto-reprocessing
- Incremental updates
- Export summaries
- Customizable prompts

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
