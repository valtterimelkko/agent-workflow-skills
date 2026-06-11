#!/usr/bin/env python3
"""Reddit credential loader following the hierarchical loading strategy.

Priority:
1. Environment variables (REDDIT_PROXY_URL)
2. a shell startup file such as ~/.bashrc
3. a shell startup file such as ~/.bashrc (REDDIT_PROXY_URL)

Matches the pattern from CREDENTIAL_LOADING_GUIDE.md.
"""
import os
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
from credentials import load_credential


class RedditCredentialNotFound(Exception):
    """Raised when Reddit credentials cannot be found."""
    pass


def load_reddit_proxy_url(required: bool = False) -> Optional[str]:
    """
    Load Reddit proxy URL using the hierarchical loading strategy.
    
    Priority order:
    1. REDDIT_PROXY_URL environment variable
    2. a shell startup file such as ~/.bashrc
    3. a shell startup file such as ~/.bashrc export REDDIT_PROXY_URL
    
    Args:
        required: If True, raises exception when not found
        
    Returns:
        Proxy URL or None if not found and not required
        
    Raises:
        RedditCredentialNotFound: If required=True and no proxy configured
    """
    value = load_credential('REDDIT_PROXY_URL', required=False)
    if value:
        return value
    if required:
        raise RedditCredentialNotFound(
            "Reddit proxy URL not found in environment variable 'REDDIT_PROXY_URL' "
            "or a shell startup file such as ~/.bashrc. Reddit scraping requires a residential proxy in cloud environments."
        )
    return None


def check_proxy_configured() -> bool:
    """Quick check if proxy is configured without raising exceptions."""
    try:
        return load_reddit_proxy_url(required=False) is not None
    except Exception:
        return False


def get_credential_sources() -> dict:
    """
    Get a summary of available credential sources for debugging.
    
    Returns:
        Dictionary with information about each credential source
    """
    return {
        'environment': {
            'REDDIT_PROXY_URL': bool(os.environ.get('REDDIT_PROXY_URL')),
        },
        'bashrc': {
            'exists': (Path.home() / '.bashrc').exists(),
        }
    }