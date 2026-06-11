#!/usr/bin/env python3
"""TwitterAPI.io credential loader following the hierarchical loading strategy.

Priority:
1. Environment variables (TWITTERAPI_KEY)
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


class TwitterAPICredentialNotFound(Exception):
    """Raised when TwitterAPI.io credentials cannot be found."""
    pass


def load_twitterapi_key(required: bool = True) -> Optional[str]:
    """
    Load TwitterAPI.io API key using the hierarchical loading strategy.

    Priority order:
    1. TWITTERAPI_KEY environment variable
    2. a shell startup file such as ~/.bashrc export TWITTERAPI_KEY
    
    Args:
        required: If True, raises exception when not found
        
    Returns:
        API key or None if not found and not required
        
    Raises:
        TwitterAPICredentialNotFound: If required=True and no API key found
    """
    value = load_credential('TWITTERAPI_KEY', required=False)
    if value:
        return value
    if required:
        raise TwitterAPICredentialNotFound(
            "TwitterAPI.io key not found in environment variable 'TWITTERAPI_KEY' "
            "or a shell startup file such as ~/.bashrc. Get your API key at: https://twitterapi.io"
        )
    return None


def check_credentials_configured() -> bool:
    """Quick check if TwitterAPI.io credentials are configured."""
    try:
        return load_twitterapi_key(required=False) is not None
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
            'TWITTERAPI_KEY': bool(os.environ.get('TWITTERAPI_KEY')),
        },
        'bashrc': {
            'exists': (Path.home() / '.bashrc').exists(),
        }
    }