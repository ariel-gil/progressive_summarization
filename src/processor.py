"""Markdown processing and summarization logic."""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
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


def parse_markdown(file_path: str) -> List[Chunk]:
    """
    Parse markdown file into level 0 chunks (paragraphs).

    Args:
        file_path: Path to markdown file

    Returns:
        List of level 0 Chunk dictionaries
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by double newlines to get paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    # Create level 0 chunks
    chunks = []
    for idx, para in enumerate(paragraphs):
        chunk = {
            "id": f"chunk_{idx}",
            "level": 0,
            "content": para,
            "parent_id": None,
            "child_ids": [],
            "position": idx
        }
        chunks.append(chunk)

    return chunks


def group_chunks(chunks: List[Chunk], group_size: int = 5) -> List[List[Chunk]]:
    """
    Group consecutive chunks for batch summarization.

    Args:
        chunks: List of chunks at the same level
        group_size: Number of chunks per group (default 5)

    Returns:
        List of chunk groups (each group is a list of chunks)
    """
    groups = []
    for i in range(0, len(chunks), group_size):
        group = chunks[i:i + group_size]
        groups.append(group)

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
    chunk_texts = [f"Section {i+1}:\n{chunk['content']}" for i, chunk in enumerate(chunks)]
    combined_text = "\n\n".join(chunk_texts)

    prompt = f"""Summarize the following text sections into a single coherent summary.
Preserve key information and maintain logical flow.

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
            new_chunk = {
                "id": f"chunk_{next_chunk_id}",
                "level": chunks[0]["level"] + 1,
                "content": summary_text,
                "parent_id": None,  # Will be set if there's a higher level
                "child_ids": [chunk["id"] for chunk in chunks],
                "position": chunks[0]["position"]  # Use first chunk's position
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

    # Parse markdown
    level_0_chunks = parse_markdown(file_path)
    print(f"Parsed {len(level_0_chunks)} paragraphs")

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
