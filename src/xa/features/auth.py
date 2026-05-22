"""Commandes d'authentification : `xa auth init`, `xa auth status`.

Note : argparse ne supporte pas les "sub-sub-commands" élégamment. On expose
donc directement `xa auth-init` et `xa auth-status` comme deux commandes
au même niveau que les autres.
"""

from __future__ import annotations

import re
import urllib.parse

from ..core.auth import load_x_cookies, read_cookies, save_cookies
from ..core.errors import XaError
from ..core.output import ok
from ..core.registry import register
from ..core.settings import BROWSERS, COOKIE_FILE
from ._common import get_client


def _configure_init(sp):
    sp.add_argument(
        "--browser",
        choices=list(BROWSERS),
        help="restreint à un navigateur (chrome/brave/edge/chromium)",
    )
    sp.add_argument("--profile", help="restreint à un profil ex: 'Profile 1'")


@register("auth-init", configure=_configure_init)
def cmd_auth_init(args) -> dict:
    """Extrait les cookies X depuis Chrome (ou Brave/Edge/Chromium)."""
    cookies = load_x_cookies(browser=args.browser, profile=args.profile)
    save_cookies(cookies)
    return ok({
        "saved_to": str(COOKIE_FILE),
        "cookie_count": len(cookies),
        "has_auth_token": "auth_token" in cookies,
        "has_ct0": "ct0" in cookies,
        "user_id": _twid_to_uid(cookies.get("twid", "")),
    })


@register("auth-status")
def cmd_auth_status(args) -> dict:
    """Vérifie que la session X est valide (test query sur @x)."""
    from ._common import get_client as _get  # avoid early import side-effects

    cookies = read_cookies()
    user_id = _twid_to_uid(cookies.get("twid", ""))
    client = _get()
    try:
        client.call("UserByScreenName", {
            "screen_name": "x", "withSafetyModeUserFields": True,
        })
    except XaError:
        raise
    except Exception as e:  # noqa: BLE001
        raise XaError(
            "session_invalid",
            f"requête test a échoué: {e}",
            hint="relance `xa auth-init`",
        )
    return ok({"user_id": user_id, "session": "valid"})


def _twid_to_uid(twid: str) -> str | None:
    m = re.search(r"u=(\d+)", urllib.parse.unquote(twid or ""))
    return m.group(1) if m else None
