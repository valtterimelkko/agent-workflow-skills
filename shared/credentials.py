#!/usr/bin/env python3
"""Shared credential loading module for skills.

Hierarchical loading strategy:
1. Environment variables (highest priority)
2. ~/.bashrc export lines (fallback)
"""

import os
from pathlib import Path
from typing import Optional


class CredentialNotFound(Exception):
    """Raised when a credential cannot be found in any source."""
    pass


def load_credential(
    env_var: str,
    bashrc_key: Optional[str] = None,
    required: bool = True
) -> Optional[str]:
    """
    Load a credential using the hierarchical loading strategy.

    Priority order:
    1. Environment variable `env_var`
    2. ~/.bashrc line `export <bashrc_key>=...` (defaults to env_var)

    Args:
        env_var: Name of the environment variable to check
        bashrc_key: Alternative key name in ~/.bashrc (defaults to env_var)
        required: If True, raises CredentialNotFound when not found

    Returns:
        The credential value, or None if not found and not required
    """
    # 1. Environment variable
    value = os.environ.get(env_var)
    if value:
        return value

    # 2. ~/.bashrc fallback
    bashrc_key = bashrc_key or env_var
    bashrc_path = Path.home() / '.bashrc'

    try:
        with open(bashrc_path, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                # Must start with export and the exact key
                prefix = f"export {bashrc_key}="
                if line.startswith(prefix):
                    # Extract everything after the first =
                    value = line.split('=', 1)[1]
                    # Strip surrounding quotes
                    value = value.strip('"\'')
                    # Strip inline shell comments
                    if ' #' in value:
                        value = value.split(' #', 1)[0].strip()
                    if value:
                        return value
    except (FileNotFoundError, PermissionError, Exception):
        pass

    if required:
        raise CredentialNotFound(
            f"Credential '{env_var}' not found in environment or ~/.bashrc"
        )
    return None


def get_env_or_bashrc(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a value from environment or ~/.bashrc, never raising.

    Args:
        var_name: Name of the variable
        default: Default value if not found

    Returns:
        The value, or default if not found
    """
    try:
        return load_credential(var_name, required=False) or default
    except Exception:
        return default
