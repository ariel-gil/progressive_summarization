"""Markdown processing and whole-document summarization."""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
from openai import AsyncOpenAI

from cache_manager import (
    load_cache,
    is_cache_valid,
    save_cache,
    compute_file_hash
)


# Type alias
DocumentCache = Dict[str, Any]


async def generate_summary(
    content: str,
    level: int,
    total_levels: int,
    api_key: str,
    model: str
) -> str:
    """
    Generate a summary at a specific abstraction level.

    Args:
        content: Full document content
        level: Target abstraction level (1=most detailed, total_levels=most abstract)
        total_levels: Total number of abstraction levels
        api_key: OpenRouter API key
        model: Model name

    Returns:
        Summary text
    """
    # Define compression targets based on level
    # Calculate target compression ratio
    compression_ratio = level / total_levels

    if level == total_levels:
        # Ultra-compressed: 1-2 paragraphs
        prompt = f"""Provide an ultra-compressed summary of the following document in 1-2 short paragraphs.
Capture only the absolute core essence and main takeaway.

Document:
{content}

Ultra-compressed summary:"""
    elif compression_ratio >= 0.85:
        # Very high compression: 2-4 paragraphs
        prompt = f"""Provide a very brief summary of the following document in 2-4 paragraphs.
Focus on the most critical points and key conclusions.

Document:
{content}

Brief summary:"""
    elif compression_ratio >= 0.65:
        # High compression: executive summary
        prompt = f"""Provide an executive summary of the following document in about 5-8 paragraphs.
Include the main points, key insights, and important conclusions.

Document:
{content}

Executive summary:"""
    elif compression_ratio >= 0.4:
        # Medium compression: comprehensive summary
        prompt = f"""Provide a comprehensive summary of the following document.
Preserve key details, important examples, and main arguments.
Target roughly {int(compression_ratio * 100)}% of the original length.

Document:
{content}

Comprehensive summary:"""
    else:
        # Low compression: detailed summary
        prompt = f"""Provide a detailed summary of the following document.
Preserve most key details, examples, nuanced points, and maintain the document structure.
Target roughly {int(compression_ratio * 100)}% of the original length.

Document:
{content}

Detailed summary:"""

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

            return response.choices[0].message.content.strip()

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"API error (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise RuntimeError(f"Failed to generate summary after {max_retries} attempts: {e}")


async def generate_all_summaries(
    content: str,
    api_key: str,
    model: str,
    num_levels: int
) -> List[Dict[str, Any]]:
    """
    Generate all abstraction levels for a document.

    Args:
        content: Full document content
        api_key: OpenRouter API key
        model: Model name
        num_levels: Number of abstraction levels (excluding original)

    Returns:
        List of document levels, from most abstract to original
    """
    # Create tasks for all summary levels (in parallel)
    tasks = []
    for level in range(1, num_levels + 1):
        task = generate_summary(content, level, num_levels, api_key, model)
        tasks.append(task)

    print(f"Generating {num_levels} abstraction levels in parallel...")
    summaries = await asyncio.gather(*tasks)

    # Build document levels list (from most abstract to most detailed)
    levels = []

    # Add summaries in reverse order (most abstract first)
    for i, summary in enumerate(reversed(summaries)):
        level_num = num_levels - i
        levels.append({
            "level": level_num,
            "content": summary,
            "is_original": False
        })

    # Add original document as level 0
    levels.append({
        "level": 0,
        "content": content,
        "is_original": True
    })

    return levels


def process_file(file_path: str, config: Dict[str, Any]) -> DocumentCache:
    """
    Process a markdown file and generate abstraction levels.

    Args:
        file_path: Path to markdown file
        config: Configuration dictionary

    Returns:
        DocumentCache with metadata and levels
    """
    cache_dir = config['cache_dir']

    # Check cache first
    cache = load_cache(file_path, cache_dir)
    if cache and is_cache_valid(cache, file_path):
        print(f"Using cached summaries for {file_path}")
        return cache

    print(f"Processing {file_path}...")

    # Read full document
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Document size: {len(content)} characters")

    # Generate all abstraction levels
    api_key = config['openrouter_api_key']
    model = config['model']
    num_levels = config['abstraction_levels']

    levels = asyncio.run(
        generate_all_summaries(content, api_key, model, num_levels)
    )

    # Create document cache
    document_cache = {
        "metadata": {
            "filename": file_path,
            "hash": compute_file_hash(file_path),
            "processed_at": datetime.now().isoformat(),
            "model": model,
            "num_levels": num_levels
        },
        "levels": levels
    }

    # Save cache
    save_cache(document_cache, file_path, cache_dir)
    print(f"Processing complete: {len(levels)} abstraction levels generated")

    return document_cache
