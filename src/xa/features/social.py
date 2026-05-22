"""Réseau social : `xa following`, `xa followers`, `xa follow`, `xa unfollow`."""

from __future__ import annotations

from ..core.output import ok, select_fields
from ..core.pagination import paginate_capped
from ..core.parsers import parse_user_entries
from ..core.registry import register
from ..core.settings import DEFAULT_LIMIT
from ._common import get_client, require_yes, resolve_user


def _configure_paginated(sp):
    sp.add_argument("screen_name")
    sp.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    sp.add_argument("--cursor")
    sp.add_argument("--fields")


def _configure_screen_yes(sp):
    sp.add_argument("screen_name")
    sp.add_argument("--yes", action="store_true",
                    help="confirme explicitement cette action visible publiquement")


def _users_paginated(args, op: str) -> dict:
    client = get_client()
    u = resolve_user(client, args.screen_name)
    rows, next_c = paginate_capped(client, op, {
        "userId": u["rest_id"],
        "includePromotedContent": False,
        "withGrokTranslatedBio": False,
    }, parse_user_entries, args.limit, args.cursor)
    return ok(select_fields(rows, args.fields),
              next_cursor=next_c, count=len(rows))


@register("following", configure=_configure_paginated)
def cmd_following(args) -> dict:
    """Comptes suivis par @screen_name."""
    return _users_paginated(args, "Following")


@register("followers", configure=_configure_paginated)
def cmd_followers(args) -> dict:
    """Comptes qui suivent @screen_name."""
    return _users_paginated(args, "Followers")


@register("follow", configure=_configure_screen_yes, is_write=True)
def cmd_follow(args) -> dict:
    """Suivre un compte (action visible publiquement, requiert --yes)."""
    require_yes(args, "follow")
    client = get_client()
    u = resolve_user(client, args.screen_name)
    r = client._raw(
        "POST",
        "https://x.com/i/api/1.1/friendships/create.json",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={"user_id": u["rest_id"], "include_profile_interstitial_type": "1"},
    )
    if r.status_code != 200:
        from ..core.errors import XaError
        raise XaError("follow_failed", f"HTTP {r.status_code}: {r.text[:200]}")
    return ok({"followed": args.screen_name, "user_id": u["rest_id"]})


@register("unfollow", configure=_configure_screen_yes, is_write=True)
def cmd_unfollow(args) -> dict:
    """Ne plus suivre un compte (requiert --yes)."""
    require_yes(args, "unfollow")
    client = get_client()
    u = resolve_user(client, args.screen_name)
    r = client._raw(
        "POST",
        "https://x.com/i/api/1.1/friendships/destroy.json",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={"user_id": u["rest_id"]},
    )
    if r.status_code != 200:
        from ..core.errors import XaError
        raise XaError("unfollow_failed", f"HTTP {r.status_code}: {r.text[:200]}")
    return ok({"unfollowed": args.screen_name, "user_id": u["rest_id"]})
