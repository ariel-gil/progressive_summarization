"""Configuration management for Progressive Summarization Viewer."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load and validate configuration from YAML file.

    Args:
        config_path: Path to config.yaml file

    Returns:
        Dictionary containing configuration settings

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            "Please create a config.yaml file with your settings."
        )

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Validate required fields
    required_fields = ['openrouter_api_key', 'model', 'abstraction_levels']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")

    # Set defaults for optional fields
    config.setdefault('chunk_strategy', 'paragraph')
    config.setdefault('group_size', 5)
    config.setdefault('cache_dir', '.summary_cache')
    config.setdefault('window_width', 800)
    config.setdefault('window_height', 600)
    config.setdefault('font_size', 12)

    # Validate values
    if config['abstraction_levels'] < 1:
        raise ValueError("abstraction_levels must be >= 1")

    if config['group_size'] < 2:
        raise ValueError("group_size must be >= 2")

    # Check API key
    if not config['openrouter_api_key'] or config['openrouter_api_key'] == "":
        # Try environment variable
        env_key = os.getenv('OPENROUTER_API_KEY')
        if env_key:
            config['openrouter_api_key'] = env_key
        else:
            raise ValueError(
                "OpenRouter API key not found. Please set it in config.yaml "
                "or as OPENROUTER_API_KEY environment variable."
            )

    return config


def get_api_key(config: Dict[str, Any]) -> str:
    """
    Get API key from config with environment variable fallback.

    Args:
        config: Configuration dictionary

    Returns:
        API key string

    Raises:
        ValueError: If no API key found
    """
    api_key = config.get('openrouter_api_key')

    if not api_key or api_key == "":
        api_key = os.getenv('OPENROUTER_API_KEY')

    if not api_key:
        raise ValueError(
            "OpenRouter API key not found. Please set it in config.yaml "
            "or as OPENROUTER_API_KEY environment variable."
        )

    return api_key
