"""Configuration management for LLM providers.

This module handles API key discovery, storage, and retrieval
from multiple sources with a clear priority order:

Priority (highest to lowest):
1. Explicit parameter (passed directly to functions)
2. Environment variable (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
3. .env file in current directory or workspace root
4. User config file (~/.config/gitsummary/config or ~/.gitsummary)
5. Interactive prompt (with option to save to config file)

The configuration is designed to be:
- Secure: Never logs or exposes API keys
- Flexible: Works in CI, local dev, and interactive modes
- Portable: Config file can be copied between machines
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

# Try to import dotenv, but don't require it
try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


# Provider-specific environment variable names
PROVIDER_ENV_VARS = {
    "openai": ["OPENAI_API_KEY", "GITSUMMARY_OPENAI_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY", "GITSUMMARY_ANTHROPIC_KEY"],
    "mistral": ["MISTRAL_API_KEY", "GITSUMMARY_MISTRAL_KEY"],
    "ollama": [],  # Ollama typically doesn't need an API key
}

# Default config file locations
CONFIG_DIR = Path.home() / ".config" / "gitsummary"
CONFIG_FILE = CONFIG_DIR / "config"
LEGACY_CONFIG_FILE = Path.home() / ".gitsummary"


@dataclass
class ProviderSettings:
    """Settings for a specific LLM provider."""

    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GlobalConfig:
    """Global gitsummary configuration."""

    # Default provider to use
    default_provider: str = "openai"

    # Provider-specific settings
    providers: Dict[str, ProviderSettings] = field(default_factory=dict)

    # Analysis settings
    use_llm: bool = True
    fallback_to_heuristic: bool = True

    def get_provider_settings(self, provider: str) -> ProviderSettings:
        """Get settings for a specific provider, creating if needed."""
        if provider not in self.providers:
            self.providers[provider] = ProviderSettings()
        return self.providers[provider]


class ConfigManager:
    """Manages gitsummary configuration including API keys.

    Handles loading from environment, .env files, and config files.
    Provides methods to prompt users for missing keys and save them.
    """

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        """Initialize the config manager.

        Args:
            workspace_root: Optional workspace root for .env file discovery.
                           If None, uses current working directory.
        """
        self.workspace_root = workspace_root or Path.cwd()
        self._config: Optional[GlobalConfig] = None
        self._env_loaded = False

    def _ensure_env_loaded(self) -> None:
        """Load .env file if not already loaded."""
        if self._env_loaded:
            return

        self._env_loaded = True

        if not DOTENV_AVAILABLE:
            return

        # Try workspace .env first, then cwd
        env_paths = [
            self.workspace_root / ".env",
            Path.cwd() / ".env",
        ]

        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path, override=False)
                break

    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from the config file."""
        config_data: Dict[str, Any] = {}

        # Try new location first, then legacy
        config_paths = [CONFIG_FILE, LEGACY_CONFIG_FILE]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and "=" in line and not line.startswith("#"):
                                key, value = line.split("=", 1)
                                config_data[key.strip()] = value.strip()
                except Exception:
                    pass  # Ignore malformed config files
                break

        return config_data

    def _save_to_config_file(self, key: str, value: str) -> bool:
        """Save a key-value pair to the config file.

        Returns True if successful, False otherwise.
        """
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Load existing config
            config_data = self._load_config_file()
            config_data[key] = value

            # Write back
            with open(CONFIG_FILE, "w") as f:
                for k, v in config_data.items():
                    f.write(f"{k}={v}\n")

            # Set restrictive permissions
            CONFIG_FILE.chmod(0o600)
            return True
        except Exception:
            return False

    def get_api_key(
        self,
        provider: str,
        prompt_if_missing: bool = False,
        save_to_config: bool = True,
    ) -> Optional[str]:
        """Get API key for a provider from various sources.

        Search order:
        1. Environment variables (provider-specific)
        2. .env file
        3. Config file
        4. Interactive prompt (if enabled)

        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            prompt_if_missing: If True, prompt user for key if not found
            save_to_config: If True and prompting, save the key to config file

        Returns:
            The API key if found, None otherwise.
        """
        # Ensure .env is loaded
        self._ensure_env_loaded()

        # Check environment variables
        env_vars = PROVIDER_ENV_VARS.get(provider, [])
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                return value

        # Check config file
        config_data = self._load_config_file()
        config_key = f"{provider.upper()}_API_KEY"
        if config_key in config_data:
            return config_data[config_key]

        # Prompt if enabled and we're in an interactive terminal
        if prompt_if_missing and _is_interactive():
            return self._prompt_for_key(provider, save_to_config)

        return None

    def _prompt_for_key(
        self,
        provider: str,
        save_to_config: bool = True,
    ) -> Optional[str]:
        """Interactively prompt the user for an API key.

        Args:
            provider: Provider name for display
            save_to_config: Whether to offer saving the key

        Returns:
            The entered API key, or None if cancelled.
        """
        import getpass

        print(f"\n🔑 No API key found for {provider}.")
        print(f"   You can set it via environment variable or enter it now.\n")

        try:
            api_key = getpass.getpass(f"Enter your {provider} API key (or press Enter to skip): ")
        except (EOFError, KeyboardInterrupt):
            print("\n   Skipped.")
            return None

        if not api_key.strip():
            return None

        api_key = api_key.strip()

        # Offer to save
        if save_to_config:
            try:
                save = input("   Save this key to ~/.config/gitsummary/config? [Y/n]: ")
                if save.lower() != "n":
                    config_key = f"{provider.upper()}_API_KEY"
                    if self._save_to_config_file(config_key, api_key):
                        print(f"   ✓ Saved to {CONFIG_FILE}")
                    else:
                        print("   ✗ Could not save to config file")
            except (EOFError, KeyboardInterrupt):
                pass

        return api_key

    def get_default_provider(self) -> str:
        """Get the default provider name."""
        # Check environment first
        env_provider = os.environ.get("GITSUMMARY_PROVIDER")
        if env_provider:
            return env_provider.lower()

        # Check config file
        config_data = self._load_config_file()
        if "DEFAULT_PROVIDER" in config_data:
            return config_data["DEFAULT_PROVIDER"].lower()

        return "openai"

    def get_provider_model(self, provider: str) -> Optional[str]:
        """Get the configured model for a provider."""
        # Check environment first
        env_var = f"GITSUMMARY_{provider.upper()}_MODEL"
        model = os.environ.get(env_var)
        if model:
            return model

        # Check config file
        config_data = self._load_config_file()
        config_key = f"{provider.upper()}_MODEL"
        return config_data.get(config_key)


def _is_interactive() -> bool:
    """Check if we're running in an interactive terminal."""
    import sys

    return sys.stdin.isatty() and sys.stdout.isatty()


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

