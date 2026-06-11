#!/usr/bin/env python3
"""Reddit credential loader following the hierarchical loading strategy.

Priority:
1. Environment variables (REDDIT_PROXY_URL, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
2. a shell startup file such as ~/.bashrc (fallback)
"""
import importlib.util
import os
from pathlib import Path
from typing import Optional

# Load shared credentials module directly to avoid name collision
_shared_spec = importlib.util.spec_from_file_location(
    "_shared_credentials",
    str(Path(__file__).resolve().parents[3] / "shared/credentials.py")
)
_shared_module = importlib.util.module_from_spec(_shared_spec)
_shared_spec.loader.exec_module(_shared_module)
load_credential = _shared_module.load_credential


class RedditCredentialNotFound(Exception):
    """Raised when Reddit credentials cannot be found."""
    pass


def load_reddit_proxy_url(required: bool = False) -> Optional[str]:
    """
    Load Reddit proxy URL using the hierarchical loading strategy.

    Priority order:
    1. REDDIT_PROXY_URL environment variable
    2. a shell startup file such as ~/.bashrc export REDDIT_PROXY_URL
    
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


def load_reddit_oauth_credentials() -> tuple[Optional[str], Optional[str]]:
    """
    Load Reddit OAuth2 credentials.
    
    Returns:
        Tuple of (client_id, client_secret) - either may be None
    """
    client_id = load_credential('REDDIT_CLIENT_ID', required=False)
    client_secret = load_credential('REDDIT_CLIENT_SECRET', required=False)
    return client_id, client_secret


def check_proxy_configured() -> bool:
    """Quick check if proxy is configured without raising exceptions."""
    try:
        return load_reddit_proxy_url(required=False) is not None
    except Exception:
        return False


def check_oauth_configured() -> bool:
    """Check if OAuth2 credentials are configured."""
    client_id, client_secret = load_reddit_oauth_credentials()
    return bool(client_id and client_secret)


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