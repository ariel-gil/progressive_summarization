# Progressive Summarization Viewer - Full Spec

## Project Overview
Desktop app that generates hierarchical summaries of markdown files and provides an interactive viewer to navigate between abstraction levels.

## Tech Stack
- **Language:** Python 3.10+
- **UI:** tkinter (built-in, simpler for MVP)
- **API:** OpenRouter (Gemini 2.5 Flash)
- **Dependencies:**
  - `openai` (for OpenRouter API calls)
  - `markdown` (for parsing)
  - `pyyaml` (for config)
  - `watchdog` (future: file watching)

## Project Structure
```
progressive-summarizer/
├── src/
│   ├── main.py                 # Entry point
│   ├── processor.py            # Summarization logic
│   ├── viewer.py               # UI components
│   ├── cache_manager.py        # Cache handling
│   └── config.py               # Configuration
├── .summary_cache/             # Generated summaries (gitignored)
├── config.yaml                 # User settings
├── requirements.txt
└── README.md
```

## Core Components

### 1. `config.py`
**Purpose:** Load and validate configuration

```python
# config.yaml structure:
openrouter_api_key: "your-key-here"
model: "google/gemini-2.0-flash-exp:free"
abstraction_levels: 3
chunk_strategy: "paragraph"  # paragraph | sentence | hybrid
cache_dir: ".summary_cache"
```

**Functions:**
- `load_config() -> dict` - Load and validate config.yaml
- `get_api_key() -> str` - Get API key with env var fallback

### 2. `processor.py`
**Purpose:** Parse markdown and generate summaries

**Data Structures:**
```python
Chunk = {
    "id": str,              # unique identifier
    "level": int,           # 0 = original, 1+ = summary levels
    "content": str,         # actual text
    "parent_id": str,       # id of parent chunk (None for level 0)
    "child_ids": [str],     # ids of children
    "position": int         # order in document
}

DocumentCache = {
    "metadata": {
        "filename": str,
        "hash": str,        # content hash for change detection
        "processed_at": str,
        "model": str
    },
    "chunks": [Chunk]       # flat list of all chunks
}
```

**Key Functions:**

`parse_markdown(file_path: str) -> list[Chunk]`
- Split markdown into paragraphs
- Create level 0 chunks with original text
- Assign sequential IDs (chunk_0, chunk_1, etc.)

`group_chunks(chunks: list[Chunk], group_size: int = 5) -> list[list[Chunk]]`
- Group consecutive chunks for batch summarization
- Return list of groups (each group = ~5 paragraphs)

`summarize_chunk_group(chunks: list[Chunk], api_key: str, model: str) -> Chunk`
- Send group to API with prompt:
  ```
  Summarize the following text sections into a single coherent summary. 
  Preserve key information and maintain logical flow.
  
  [chunk texts here]
  
  Provide only the summary, no preamble.
  ```
- Create new Chunk with level+1, link to children
- Use async/parallel requests (10 concurrent max)

`build_summary_tree(level_0_chunks: list[Chunk], api_key: str, model: str, max_level: int) -> list[Chunk]`
- Bottom-up algorithm:
  1. Start with level 0 (original paragraphs)
  2. Group into batches of 5
  3. Parallel API calls to create level 1 summaries
  4. Repeat: group level 1 summaries → create level 2
  5. Continue until one chunk remains or max_level reached
- Return flat list of all chunks (all levels)

`process_file(file_path: str, config: dict) -> DocumentCache`
- Orchestrates full processing pipeline
- Check cache first (see cache_manager)
- Parse → build tree → return DocumentCache

### 3. `cache_manager.py`
**Purpose:** Manage summary cache

**Functions:**

`get_cache_path(file_path: str, cache_dir: str) -> str`
- Convert `/path/to/doc.md` → `.summary_cache/doc_md_cache.json`

`compute_file_hash(file_path: str) -> str`
- SHA256 hash of file contents

`load_cache(file_path: str, cache_dir: str) -> DocumentCache | None`
- Load cached summaries if exist
- Return None if doesn't exist

`is_cache_valid(cache: DocumentCache, file_path: str) -> bool`
- Compare cached hash with current file hash
- Return False if file changed

`save_cache(cache: DocumentCache, file_path: str, cache_dir: str)`
- Write DocumentCache to JSON

### 4. `viewer.py`
**Purpose:** Interactive UI

**UI Layout:**
```
┌─────────────────────────────────────────────┐
│ File: document.md                      [X]  │
├─────────────────────────────────────────────┤
│ Abstraction Level: [====|====] (Level 2/3)  │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Summary Block 1                     │   │
│  │ [Click to zoom in]                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Summary Block 2                     │   │
│  │ [Click to zoom in]                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
├─────────────────────────────────────────────┤
│ Breadcrumb: Doc > Section 2 > [Current]    │
└─────────────────────────────────────────────┘
```

**Key Classes:**

`class SummaryViewer(tk.Tk)`
- Main window
- Properties:
  - `document_cache: DocumentCache`
  - `current_level: int`
  - `current_parent: str | None` (for zoom-in navigation)
  - `breadcrumb_trail: list[str]`

**Key Methods:**

`__init__(self, file_path: str, config: dict)`
- Load/process document
- Setup UI components

`render_level(self, level: int, parent_id: str = None)`
- Filter chunks by level and parent
- Display in scrollable frame
- Each chunk = clickable Text widget

`on_slider_change(self, value: int)`
- Update current_level
- Call render_level()

`on_chunk_click(self, chunk_id: str)`
- If chunk has children:
  - Add to breadcrumb
  - Zoom to next level down with this chunk as parent
  - Update display

`on_breadcrumb_click(self, index: int)`
- Navigate back up hierarchy
- Reset to clicked level

### 5. `main.py`
**Purpose:** Entry point

```python
def main():
    # Check for config
    config = load_config()
    
    # File picker dialog
    file_path = filedialog.askopenfilename(
        filetypes=[("Markdown", "*.md")]
    )
    
    if not file_path:
        return
    
    # Show loading window
    show_processing_dialog()
    
    # Process in background thread
    cache = process_file(file_path, config)
    
    # Launch viewer
    viewer = SummaryViewer(file_path, config)
    viewer.mainloop()
```

## Processing Algorithm Details

**Bottom-Up Summarization Flow:**
```
Level 0: [P1] [P2] [P3] [P4] [P5] [P6] [P7] [P8] [P9] [P10]
          │    │    │    │    │    │    │    │    │    │
          └────┴────┘    └────┴────┘    └────┴────┘    │
                │              │              │         │
Level 1:      [S1]           [S2]           [S3]      [S4]
                │              │              │         │
                └──────────────┴──────────────┴─────────┘
                                     │
Level 2:                           [S5]
```

**Parallelization:**
- Process each level in parallel batches
- Wait for all level N summaries before starting level N+1
- Use `asyncio` with `aiohttp` for concurrent API calls

## API Integration

**OpenRouter Setup:**
```python
import openai

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=config["openrouter_api_key"]
)

response = client.chat.completions.create(
    model="google/gemini-2.0-flash-exp:free",
    messages=[
        {"role": "user", "content": prompt}
    ]
)
```

**Rate Limiting:**
- Max 10 concurrent requests
- Add 0.1s delay between batches
- Retry with exponential backoff on failures

## Configuration File

**config.yaml:**
```yaml
openrouter_api_key: ""  # User must fill this

# Model settings
model: "google/gemini-2.0-flash-exp:free"
abstraction_levels: 3

# Processing settings
chunk_strategy: "paragraph"
group_size: 5  # chunks per summary

# Cache settings
cache_dir: ".summary_cache"

# UI settings
window_width: 800
window_height: 600
font_size: 12
```

## Implementation Priority

**Phase 1 (MVP - Essential):**
1. `config.py` - Configuration loading
2. `cache_manager.py` - Basic caching
3. `processor.py` - Parse markdown + bottom-up summarization
4. `viewer.py` - Basic UI with slider
5. `main.py` - Entry point with file picker

**Phase 2 (Enhancements):**
- Click-to-zoom navigation
- Breadcrumb trail
- Better error handling
- Progress indicators during processing

**Phase 3 (Future):**
- File watching for auto-reprocessing
- Incremental updates
- Export summaries
- Customizable prompts

## Error Handling

**Critical Errors (show dialog + exit):**
- Missing API key
- Invalid markdown file
- API failures after retries

**Recoverable Errors (show warning + continue):**
- Cache corruption (regenerate)
- Individual chunk summarization failure (skip)

## Testing Checklist

1. Process small file (5 paragraphs)
2. Process large file (50+ paragraphs)
3. Cache hit/miss behavior
4. File modification detection
5. Slider navigation
6. API error recovery

## Requirements.txt
```
openai>=1.0.0
pyyaml>=6.0
markdown>=3.4.0
```

---

**Note for Claude Code:** Start with Phase 1. Use type hints throughout. Add docstrings to all functions. Handle errors gracefully with try/except blocks.