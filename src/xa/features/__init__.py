"""Tous les modules de ce package contiennent des `@register` decorateurs.

L'import du package (`from xa import features`) déclenche tous les decorators,
ce qui peuple `core.registry.COMMANDS`.
"""

# L'ordre est libre : seuls les @register comptent. On les nomme tous pour
# que l'import déclenche bien tous les decorateurs.
from . import (  # noqa: F401
    auth,
    content,
    cookies,
    discovery,
    engage,
    harvest,
    identity,
    raw,
    social,
)
