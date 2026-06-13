"""Constantes globales : Bearer X, config dir, limites, navigateurs supportés."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import browser_cookie3

# Bearer "public" du client web x.com (constante depuis ~2014, change rarement).
# Extrait du JS principal de x.com.
BEARER = (
    "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xn"
    "Zz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)


def _default_cfg_dir() -> Path:
    """Répertoire config par OS.

    - macOS / Linux : `$XDG_CONFIG_HOME/xa` ou `~/.config/xa`
    - Windows       : `%APPDATA%\\xa` (ou `~\\AppData\\Roaming\\xa` en fallback)
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "xa"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "xa"


# Répertoire de config utilisateur (cookies, features persistées)
CFG_DIR = _default_cfg_dir()
COOKIE_FILE = CFG_DIR / "cookies.json"
FEATURES_FILE = CFG_DIR / "features.json"

# Cache local du corpus de signets (pour la recherche locale `--grep`).
BOOKMARKS_CACHE_FILE = CFG_DIR / "bookmarks-cache.json"
BOOKMARKS_CACHE_TTL = 600  # secondes ; au-delà on repagine (sauf --refresh)

# Pagination defaults
DEFAULT_LIMIT = 50
MAX_LIMIT = 1000


def _user_data_root(macos: str, windows: str, linux: str) -> Path:
    """Construit le chemin `User Data` Chromium pour l'OS courant."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / macos
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / windows
    return Path.home() / ".config" / linux


# Navigateurs Chromium dont on sait lire les cookies.
# Pour chaque navigateur : (root `User Data` selon l'OS, fn browser_cookie3).
# Les profils sont des sous-dossiers `Default`, `Profile 1`, ... sous ce root.
BROWSERS: dict[str, tuple[Path, object]] = {
    "chrome": (
        _user_data_root("Google/Chrome", "Google/Chrome/User Data", "google-chrome"),
        browser_cookie3.chrome,
    ),
    "brave": (
        _user_data_root(
            "BraveSoftware/Brave-Browser",
            "BraveSoftware/Brave-Browser/User Data",
            "BraveSoftware/Brave-Browser",
        ),
        browser_cookie3.brave,
    ),
    "edge": (
        _user_data_root("Microsoft Edge", "Microsoft/Edge/User Data", "microsoft-edge"),
        browser_cookie3.edge,
    ),
    "chromium": (
        _user_data_root("Chromium", "Chromium/User Data", "chromium"),
        browser_cookie3.chromium,
    ),
}


def _default_user_agent() -> str:
    """UA Chrome plausible selon l'OS — réduit les chances d'anti-bot tagging."""
    if sys.platform == "win32":
        platform = "Windows NT 10.0; Win64; x64"
    elif sys.platform == "darwin":
        platform = "Macintosh; Intel Mac OS X 10_15_7"
    else:
        platform = "X11; Linux x86_64"
    return (
        f"Mozilla/5.0 ({platform}) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )


USER_AGENT = _default_user_agent()
