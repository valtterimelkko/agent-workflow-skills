#!/usr/bin/env python3
"""
Xpoz credential loader with fallback chain.

Credential Loading Order:
1. PRIMARY: ~/.xpoz/token.txt
2. SECONDARY: XPOZ_BEARER_TOKEN env var or a shell startup file such as ~/.bashrc
"""
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
from credentials import load_credential


class XpozCredentialLoader:
    """Load Xpoz Bearer token with fallback chain."""

    XPOZ_CONFIG_DIR = Path.home() / ".xpoz"

    def load(self) -> str:
        """
        Load Bearer token with fallback chain.

        Returns:
            Bearer token string

        Raises:
            CredentialNotFoundError: If token not found in any location
        """
        # PRIMARY: Check ~/.xpoz/
        token = self._load_from_config_dir()
        if token:
            return token

        # SECONDARY: Check env var / a shell startup file such as ~/.bashrc
        token = load_credential('XPOZ_BEARER_TOKEN', required=False)
        if token:
            # Sync back to config dir for faster future access
            self._save_to_config_dir(token)
            return token

        raise CredentialNotFoundError(
            "Xpoz token not found.\n"
            "Complete OAuth setup at https://www.xpoz.ai/ and save token to:\n"
            f"  - {self.XPOZ_CONFIG_DIR / 'token.txt'}\n"
            "Or set XPOZ_BEARER_TOKEN in your environment or a shell startup file such as ~/.bashrc.\n"
            "See: ~/.xpoz/SETUP_INSTRUCTIONS.md for details."
        )

    def _load_from_config_dir(self) -> Optional[str]:
        """Load token from ~/.xpoz/token.txt."""
        token_file = self.XPOZ_CONFIG_DIR / "token.txt"
        if token_file.exists():
            token = token_file.read_text().strip()
            if token:
                return token
        return None

    def _save_to_config_dir(self, token: str) -> None:
        """Save token to ~/.xpoz/token.txt."""
        self.XPOZ_CONFIG_DIR.mkdir(mode=0o700, exist_ok=True)
        token_file = self.XPOZ_CONFIG_DIR / "token.txt"
        token_file.write_text(token)
        token_file.chmod(0o600)

    def save_token(self, token: str) -> None:
        """
        Save token to config dir.

        Args:
            token: Bearer token to save
        """
        self._save_to_config_dir(token)
        print(f"Token saved to {self.XPOZ_CONFIG_DIR / 'token.txt'}")

    def is_configured(self) -> bool:
        """Check if credentials are available."""
        try:
            self.load()
            return True
        except CredentialNotFoundError:
            return False


class CredentialNotFoundError(Exception):
    """Raised when Xpoz credentials are not found."""
    pass
