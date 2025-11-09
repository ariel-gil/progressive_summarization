"""Markdown processing and summarization logic."""

import asyncio
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import openai
from openai import AsyncOpenAI

from cache_manager import (
    load_cache,
    is_cache_valid,
    save_cache,
    compute_file_hash
)


# Type aliases for clarity
Chunk = Dict[str, Any]
DocumentCache = Dict[str, Any]


def parse_markdown_with_headers(file_path: str) -> List[Chunk]:
    """
    Parse markdown file into semantic chunks based on headers and content.

    Uses a hybrid approach:
    1. If markdown has headers, group paragraphs under headers as natural topics
    2. If no headers, fall back to intelligent paragraph grouping

    Args:
        file_path: Path to markdown file

    Returns:
        List of level 0 Chunk dictionaries with topic/header awareness
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into lines to detect headers
    lines = content.split('\n')

    # Regex to detect markdown headers: # ## ### etc.
    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

    # First, detect if document has headers
    has_headers = any(header_pattern.match(line) for line in lines)

    if has_headers:
        return _parse_with_headers(lines, header_pattern)
    else:
        return _parse_without_headers(content)


def _parse_with_headers(lines: List[str], header_pattern) -> List[Chunk]:
    """
    Parse markdown with header-based chunking.

    Groups content under headers as topic-based chunks, but breaks large
    sections into smaller paragraph-based chunks for better granularity.
    """
    chunks = []
    chunk_id = 0
    current_header = None
    current_header_level = 0
    section_paragraphs = []
    position = 0

    for line in lines:
        header_match = header_pattern.match(line)

        if header_match:
            # Found a new header - save previous section's paragraphs
            if section_paragraphs:
                chunks.extend(_create_paragraphs_chunks(
                    section_paragraphs, current_header, current_header_level,
                    chunk_id, position
                ))
                chunk_id += len([p for p in section_paragraphs if p.strip()])
                position += len([p for p in section_paragraphs if p.strip()])
                section_paragraphs = []

            # Extract header info
            header_symbols = header_match.group(1)
            header_text = header_match.group(2).strip()
            current_header_level = len(header_symbols)
            current_header = header_text

        else:
            # Accumulate lines for paragraph detection
            section_paragraphs.append(line)

    # Save final section
    if section_paragraphs:
        chunks.extend(_create_paragraphs_chunks(
            section_paragraphs, current_header, current_header_level,
            chunk_id, position
        ))

    return chunks


def _create_paragraphs_chunks(lines: List[str], header: str, header_level: int,
                             chunk_id: int, position: int) -> List[Chunk]:
    """
    Create chunks from section content by breaking into paragraphs.

    Each paragraph under a header becomes a separate chunk for better granularity.
    """
    chunks = []
    paragraphs = [p.strip() for p in '\n'.join(lines).split('\n\n') if p.strip()]

    for para in paragraphs:
        if para:  # Skip empty paragraphs
            chunk = {
                "id": f"chunk_{chunk_id}",
                "level": 0,
                "content": para,
                "parent_id": None,
                "child_ids": [],
                "position": position,
                "header": header,
                "header_level": header_level
            }
            chunks.append(chunk)
            chunk_id += 1
            position += 1

    return chunks


def _parse_without_headers(content: str) -> List[Chunk]:
    """
    Parse markdown without headers - fall back to paragraph-based chunking.

    Groups paragraphs intelligently based on length and density.
    """
    # Split by double newlines to get logical paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    # Group small paragraphs together to avoid too many tiny chunks
    chunks = []
    chunk_id = 0
    position = 0
    current_group = []
    current_length = 0
    min_chunk_size = 200  # Minimum characters per chunk
    max_chunk_size = 1500  # Maximum before we force a break

    for para in paragraphs:
        current_group.append(para)
        current_length += len(para)

        # Create chunk if we've hit limits
        should_chunk = (
            (current_length >= max_chunk_size) or  # Too long
            (len(current_group) >= 5)  # Too many paragraphs
        )

        if should_chunk and current_group:
            content_text = '\n\n'.join(current_group)
            chunk = {
                "id": f"chunk_{chunk_id}",
                "level": 0,
                "content": content_text,
                "parent_id": None,
                "child_ids": [],
                "position": position,
                "header": None,
                "header_level": 0
            }
            chunks.append(chunk)
            chunk_id += 1
            position += 1
            current_group = []
            current_length = 0

    # Save remaining
    if current_group:
        content_text = '\n\n'.join(current_group)
        chunk = {
            "id": f"chunk_{chunk_id}",
            "level": 0,
            "content": content_text,
            "parent_id": None,
            "child_ids": [],
            "position": position,
            "header": None,
            "header_level": 0
        }
        chunks.append(chunk)

    return chunks


def parse_markdown(file_path: str) -> List[Chunk]:
    """
    Parse markdown file into level 0 chunks using smart header-based chunking.

    Args:
        file_path: Path to markdown file

    Returns:
        List of level 0 Chunk dictionaries
    """
    return parse_markdown_with_headers(file_path)


def group_chunks(chunks: List[Chunk], group_size: int = 5) -> List[List[Chunk]]:
    """
    Group consecutive chunks intelligently for batch summarization.

    Respects topic/header boundaries - doesn't split sections across groups
    unless a single section is larger than group_size.

    Args:
        chunks: List of chunks at the same level
        group_size: Target number of chunks per group (soft limit)

    Returns:
        List of chunk groups (each group is a list of chunks)
    """
    if not chunks:
        return []

    groups = []
    current_group = []
    current_group_size = 0

    for chunk in chunks:
        # Check if we should start a new group
        # Only split if current group is full OR we have a topic change at this chunk
        if (current_group_size >= group_size and current_group):
            groups.append(current_group)
            current_group = [chunk]
            current_group_size = 1
        else:
            current_group.append(chunk)
            current_group_size += 1

    # Add remaining group
    if current_group:
        groups.append(current_group)

    return groups


async def summarize_chunk_group(
    chunks: List[Chunk],
    api_key: str,
    model: str,
    next_chunk_id: int
) -> Chunk:
    """
    Summarize a group of chunks using OpenRouter API.

    Args:
        chunks: List of chunks to summarize together
        api_key: OpenRouter API key
        model: Model name (e.g., "google/gemini-2.0-flash-exp:free")
        next_chunk_id: ID counter for new chunk

    Returns:
        New summary Chunk with level+1
    """
    # Build prompt with all chunk contents
    chunk_texts = []
    for i, chunk in enumerate(chunks):
        header_info = f" ({chunk.get('header', 'Untitled')})" if chunk.get('header') else ""
        chunk_texts.append(f"Section {i+1}{header_info}:\n{chunk['content']}")

    combined_text = "\n\n".join(chunk_texts)

    prompt = f"""Summarize the following text sections into a single coherent summary.
Preserve key information and maintain logical flow. Keep the same narrative structure where possible.

{combined_text}

Provide only the summary, no preamble."""

    # Initialize async OpenAI client
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    # Call API with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )

            summary_text = response.choices[0].message.content.strip()

            # Create new chunk
            # Use first chunk's header if all chunks are from same section
            header = None
            header_level = 0
            if all(c.get('header') == chunks[0].get('header') for c in chunks):
                header = chunks[0].get('header')
                header_level = chunks[0].get('header_level', 0)

            new_chunk = {
                "id": f"chunk_{next_chunk_id}",
                "level": chunks[0]["level"] + 1,
                "content": summary_text,
                "parent_id": None,
                "child_ids": [chunk["id"] for chunk in chunks],
                "position": chunks[0]["position"],
                "header": header,
                "header_level": header_level
            }

            # Update children to point to this parent
            for chunk in chunks:
                chunk["parent_id"] = new_chunk["id"]

            return new_chunk

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"API error (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise RuntimeError(f"Failed to summarize chunk group after {max_retries} attempts: {e}")


async def build_summary_tree(
    level_0_chunks: List[Chunk],
    api_key: str,
    model: str,
    max_level: int,
    group_size: int = 5
) -> List[Chunk]:
    """
    Build summary tree using bottom-up algorithm.

    Args:
        level_0_chunks: Original paragraph chunks
        api_key: OpenRouter API key
        model: Model name
        max_level: Maximum abstraction level
        group_size: Chunks per summary group

    Returns:
        Flat list of all chunks (all levels combined)
    """
    all_chunks = level_0_chunks.copy()
    current_level_chunks = level_0_chunks.copy()
    next_chunk_id = len(level_0_chunks)  # Start IDs after level 0

    current_level = 0

    while current_level < max_level and len(current_level_chunks) > 1:
        print(f"Processing level {current_level + 1} (grouping {len(current_level_chunks)} chunks)...")

        # Group chunks
        groups = group_chunks(current_level_chunks, group_size)

        # Process groups in parallel with rate limiting
        max_concurrent = 10
        semaphore = asyncio.Semaphore(max_concurrent)

        async def summarize_with_limit(group, chunk_id):
            async with semaphore:
                result = await summarize_chunk_group(group, api_key, model, chunk_id)
                await asyncio.sleep(0.1)  # Rate limiting
                return result

        # Create tasks for all groups
        tasks = [
            summarize_with_limit(group, next_chunk_id + i)
            for i, group in enumerate(groups)
        ]

        # Wait for all summaries at this level
        new_level_chunks = await asyncio.gather(*tasks)

        # Add to all chunks and prepare for next level
        all_chunks.extend(new_level_chunks)
        current_level_chunks = new_level_chunks
        next_chunk_id += len(new_level_chunks)
        current_level += 1

        print(f"Level {current_level} complete: created {len(new_level_chunks)} summaries")

    return all_chunks


def process_file(file_path: str, config: Dict[str, Any]) -> DocumentCache:
    """
    Orchestrate full processing pipeline for a markdown file.

    Checks cache first, then parses and builds summary tree if needed.

    Args:
        file_path: Path to markdown file
        config: Configuration dictionary

    Returns:
        DocumentCache with metadata and all chunks
    """
    cache_dir = config['cache_dir']

    # Check cache first
    cache = load_cache(file_path, cache_dir)
    if cache and is_cache_valid(cache, file_path):
        print(f"Using cached summaries for {file_path}")
        return cache

    print(f"Processing {file_path}...")

    # Parse markdown with smart chunking
    level_0_chunks = parse_markdown(file_path)
    print(f"Parsed {len(level_0_chunks)} semantic chunks")

    # Build summary tree
    api_key = config['openrouter_api_key']
    model = config['model']
    max_level = config['abstraction_levels']
    group_size = config['group_size']

    # Run async tree building
    all_chunks = asyncio.run(
        build_summary_tree(level_0_chunks, api_key, model, max_level, group_size)
    )

    # Create document cache
    document_cache = {
        "metadata": {
            "filename": file_path,
            "hash": compute_file_hash(file_path),
            "processed_at": datetime.now().isoformat(),
            "model": model
        },
        "chunks": all_chunks
    }

    # Save cache
    save_cache(document_cache, file_path, cache_dir)
    print(f"Processing complete: {len(all_chunks)} total chunks")

    return document_cache
