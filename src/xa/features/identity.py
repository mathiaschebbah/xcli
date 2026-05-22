"""Identité : `xa whoami`, `xa user <screen_name>`."""

from __future__ import annotations

from ..core.errors import XaError
from ..core.output import ok, select_fields
from ..core.parsers import coalesce_user_field
from ..core.registry import register
from ._common import get_client, resolve_user


def _args_user(sp):
    sp.add_argument("screen_name")
    sp.add_argument("--fields", help="ex: screen_name,description,followers_count")


@register("whoami")
def cmd_whoami(args) -> dict:
    """Profil du compte X actuellement loggé (depuis le cookie twid)."""
    client = get_client()
    who = client.whoami()
    if not who:
        raise XaError("no_session", "cookie twid manquant",
                      hint="relance `xa auth-init`")
    data = client.call("UserByRestId", {
        "userId": who["user_id"],
        "withSafetyModeUserFields": True,
    })
    u = (data.get("data", {}).get("user", {}) or {}).get("result", {}) or {}
    legacy = u.get("legacy", {})
    return ok({
        "user_id": u.get("rest_id"),
        "screen_name": coalesce_user_field(u, "screen_name"),
        "name": coalesce_user_field(u, "name"),
        "followers_count": legacy.get("followers_count"),
        "friends_count": legacy.get("friends_count"),
        "statuses_count": legacy.get("statuses_count"),
    })


@register("user", configure=_args_user)
def cmd_user(args) -> dict:
    """Profil détaillé d'un compte X par screen_name."""
    client = get_client()
    u = resolve_user(client, args.screen_name)
    legacy = u.get("legacy", {})
    data = {
        "rest_id": u.get("rest_id"),
        "screen_name": coalesce_user_field(u, "screen_name"),
        "name": coalesce_user_field(u, "name"),
        "is_blue_verified": u.get("is_blue_verified"),
        "description": legacy.get("description"),
        "followers_count": legacy.get("followers_count"),
        "friends_count": legacy.get("friends_count"),
        "statuses_count": legacy.get("statuses_count"),
        "media_count": legacy.get("media_count"),
        "favourites_count": legacy.get("favourites_count"),
        "location": legacy.get("location"),
        "url": legacy.get("url"),
        "created_at": coalesce_user_field(u, "created_at"),
        "profile_image_url": (u.get("avatar") or {}).get("image_url"),
        "profile_banner_url": legacy.get("profile_banner_url"),
        "pinned_tweet_ids": legacy.get("pinned_tweet_ids_str", []),
    }
    return ok(select_fields(data, args.fields))
