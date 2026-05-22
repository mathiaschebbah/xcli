"""Helpers partagés par les features : _client(), _resolve_user(), _require_yes()."""

from __future__ import annotations

from ..core.auth import read_cookies
from ..core.client import XClient
from ..core.errors import XaError
from ..core.ops import load_ops


def get_client() -> XClient:
    """Construit un XClient depuis les cookies sauvegardés."""
    return XClient(read_cookies(), load_ops())


def resolve_user(client: XClient, screen_name: str) -> dict:
    """Résout @screen_name → noeud `user.result` GraphQL (avec rest_id, legacy, core)."""
    data = client.call("UserByScreenName", {
        "screen_name": screen_name.lstrip("@"),
        "withSafetyModeUserFields": True,
    })
    u = (data.get("data", {}).get("user", {}) or {}).get("result", {}) or {}
    if not u or not u.get("rest_id"):
        raise XaError(
            "user_not_found",
            f"@{screen_name} introuvable",
            hint="vérifie le screen_name (sans @)",
        )
    return u


def require_yes(args, action: str) -> None:
    """Vérifie que `--yes` est présent, sinon raise XaError."""
    if not getattr(args, "yes", False):
        raise XaError(
            "confirmation_required",
            f"l'action '{action}' modifie ton compte X et requiert --yes",
            hint="ajoute --yes pour confirmer explicitement",
        )
