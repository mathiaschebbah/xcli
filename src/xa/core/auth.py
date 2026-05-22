"""Extraction et persistance des cookies de session X.

Scanne tous les profils Chromium installés (Chrome, Brave, Edge, Chromium)
sur macOS, et retourne le premier qui contient les cookies `auth_token` +
`ct0`. Sauvegarde dans `~/.config/xa/cookies.json` en mode 0600.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

from .errors import XaError
from .settings import BROWSERS, CFG_DIR, COOKIE_FILE


def discover_browser_profiles() -> list[tuple[str, str, Path]]:
    """Retourne la liste `(browser, profile, path Cookies)` des profils trouvés.

    macOS seulement pour l'instant. Sur d'autres OS, retourne [].
    """
    home = Path.home() / "Library" / "Application Support"
    if not home.exists():
        return []
    found: list[tuple[str, str, Path]] = []
    for browser, (subpath, _fn) in BROWSERS.items():
        root = home / subpath
        if not root.exists():
            continue
        for profile_dir in sorted(root.iterdir()):
            name = profile_dir.name
            if name != "Default" and not name.startswith("Profile "):
                continue
            ck = profile_dir / "Cookies"
            if not ck.exists():
                ck = profile_dir / "Network" / "Cookies"  # Chrome moderne
            if ck.exists():
                found.append((browser, name, ck))
    return found


def load_x_cookies(
    browser: str | None = None,
    profile: str | None = None,
) -> dict[str, str]:
    """Trouve les cookies X dans le 1er profil contenant `auth_token` + `ct0`.

    Raises:
        XaError(no_cookies): aucun profil n'a les cookies requis.
    """
    candidates = discover_browser_profiles()
    if browser:
        candidates = [c for c in candidates if c[0] == browser]
    if profile:
        candidates = [c for c in candidates if c[1] == profile]
    if not candidates:
        raise XaError(
            "no_cookies",
            "Aucun profil navigateur trouvé sur le système.",
            hint="installe Chrome (ou Brave/Edge/Chromium) et connecte-toi sur https://x.com",
        )

    errors = []
    for br, prof, ck_path in candidates:
        fn = BROWSERS[br][1]
        for dom in (".x.com", ".twitter.com"):
            try:
                jar = fn(cookie_file=str(ck_path), domain_name=dom.lstrip("."))
            except Exception as e:
                errors.append(f"{br}/{prof} [{dom}]: {type(e).__name__}: {e}")
                continue
            cookies = {c.name: c.value for c in jar}
            if "auth_token" in cookies and "ct0" in cookies:
                sys.stderr.write(
                    f"[auth] cookies trouvés dans {br}/{prof} ({dom}, "
                    f"{len(cookies)} cookies)\n"
                )
                return cookies

    msg = (
        "Aucun profil ne contient les cookies X requis (auth_token + ct0). "
        "Connecte-toi sur https://x.com puis relance."
    )
    if errors:
        msg += "\nErreurs: " + " | ".join(errors[:5])
    raise XaError("no_cookies", msg, hint="login sur x.com via Chrome")


def save_cookies(cookies: dict[str, str]) -> None:
    """Persiste les cookies dans `~/.config/xa/cookies.json` (mode 0600).

    Ouvre le fichier avec 0o600 dès la création pour éviter une fenêtre
    où il serait lisible par d'autres utilisateurs.
    """
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(
        COOKIE_FILE,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(cookies, indent=2))


def twid_to_uid(twid: str) -> str | None:
    """Extrait le user_id depuis le cookie `twid` (format `u%3D<id>`)."""
    m = re.search(r"u=(\d+)", urllib.parse.unquote(twid or ""))
    return m.group(1) if m else None


def read_cookies() -> dict[str, str]:
    """Charge les cookies sauvegardés. Erreur typée si manquants."""
    if not COOKIE_FILE.exists():
        raise XaError(
            "auth_required",
            "Pas de cookies sauvegardés.",
            hint="lance `xa auth-init` pour les extraire depuis Chrome",
        )
    return json.loads(COOKIE_FILE.read_text())
