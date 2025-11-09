"""Entry point for Progressive Summarization Viewer - Web Version."""

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from web_app import run_server

if __name__ == "__main__":
    run_server()
