"""Constantes globales : Bearer X, config dir, limites, navigateurs supportés."""

from __future__ import annotations

import os
from pathlib import Path

import browser_cookie3

# Bearer "public" du client web x.com (constante depuis ~2014, change rarement).
# Extrait du JS principal de x.com.
BEARER = (
    "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xn"
    "Zz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# Répertoire de config utilisateur (cookies, features persistées)
CFG_DIR = (
    Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "xa"
)
COOKIE_FILE = CFG_DIR / "cookies.json"
FEATURES_FILE = CFG_DIR / "features.json"

# Cache local du corpus de signets (pour la recherche locale `--grep`).
BOOKMARKS_CACHE_FILE = CFG_DIR / "bookmarks-cache.json"
BOOKMARKS_CACHE_TTL = 600  # secondes ; au-delà on repagine (sauf --refresh)

# Pagination defaults
DEFAULT_LIMIT = 50
MAX_LIMIT = 1000

# Navigateurs Chromium dont on sait lire les cookies (macOS Keychain).
# (subpath sous ~/Library/Application Support, fonction browser_cookie3)
BROWSERS = {
    "chrome":   ("Google/Chrome",                browser_cookie3.chrome),
    "brave":    ("BraveSoftware/Brave-Browser",  browser_cookie3.brave),
    "edge":     ("Microsoft Edge",               browser_cookie3.edge),
    "chromium": ("Chromium",                     browser_cookie3.chromium),
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
