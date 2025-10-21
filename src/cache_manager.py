"""Cache management for Progressive Summarization Viewer."""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional


def get_cache_path(file_path: str, cache_dir: str) -> str:
    """
    Generate cache file path for a given document.

    Converts /path/to/doc.md -> .summary_cache/doc_md_cache.json

    Args:
        file_path: Path to source markdown file
        cache_dir: Directory for cache files

    Returns:
        Path to cache file
    """
    # Get filename without directory
    filename = Path(file_path).name

    # Replace dots and special chars with underscores
    safe_name = filename.replace('.', '_')

    # Create cache filename
    cache_filename = f"{safe_name}_cache.json"

    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)

    return os.path.join(cache_dir, cache_filename)


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA256 hash of file contents.

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal hash string
    """
    sha256 = hashlib.sha256()

    with open(file_path, 'rb') as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_cache(file_path: str, cache_dir: str) -> Optional[Dict[str, Any]]:
    """
    Load cached document summaries if they exist.

    Args:
        file_path: Path to source markdown file
        cache_dir: Directory for cache files

    Returns:
        DocumentCache dictionary or None if doesn't exist
    """
    cache_path = get_cache_path(file_path, cache_dir)

    if not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        return cache
    except (json.JSONDecodeError, IOError) as e:
        # Cache corrupted, return None to trigger regeneration
        print(f"Warning: Cache corrupted ({e}), will regenerate")
        return None


def is_cache_valid(cache: Dict[str, Any], file_path: str) -> bool:
    """
    Check if cached summaries are still valid.

    Compares cached hash with current file hash.

    Args:
        cache: DocumentCache dictionary
        file_path: Path to source markdown file

    Returns:
        True if cache is valid, False if file changed
    """
    if not cache or 'metadata' not in cache:
        return False

    cached_hash = cache['metadata'].get('hash')
    if not cached_hash:
        return False

    current_hash = compute_file_hash(file_path)

    return cached_hash == current_hash


def save_cache(cache: Dict[str, Any], file_path: str, cache_dir: str) -> None:
    """
    Save DocumentCache to JSON file.

    Args:
        cache: DocumentCache dictionary
        file_path: Path to source markdown file
        cache_dir: Directory for cache files
    """
    cache_path = get_cache_path(file_path, cache_dir)

    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)

    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Warning: Failed to save cache: {e}")
