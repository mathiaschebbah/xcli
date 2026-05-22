"""Découverte : `xa trends`, `xa ops [--filter]`, `xa help [cmd]`."""

from __future__ import annotations

from ..core.errors import XaError
from ..core.ops import load_ops
from ..core.output import ok
from ..core.registry import COMMANDS, register
from ._common import get_client


def _configure_ops(sp):
    sp.add_argument("--filter", help="filtre les ops dont le nom contient X")


def _configure_help(sp):
    sp.add_argument("cmd_name", nargs="?", help="nom d'une commande spécifique")


@register("trends")
def cmd_trends(args) -> dict:
    """Tendances X récentes."""
    client = get_client()
    data = client.call("TrendHistory", {})
    return ok(data.get("data") or data)


@register("ops", configure=_configure_ops)
def cmd_ops(args) -> dict:
    """Liste les opérations GraphQL connues dans le catalogue (158)."""
    ops = load_ops()
    items = list(ops.values())
    if args.filter:
        f = args.filter.lower()
        items = [o for o in items if f in o["operationName"].lower()]
    out = [{
        "operationName": o["operationName"],
        "queryId": o["queryId"],
        "operationType": o["operationType"],
    } for o in items]
    return ok(out, count=len(out), total=len(ops))


@register("help", configure=_configure_help)
def cmd_help(args) -> dict:
    """Schéma machine-readable de toutes les commandes (ou d'une seule)."""
    schema = {
        c.name: {"description": c.description,
                 "type": "write" if c.is_write else "read"}
        for c in sorted(COMMANDS, key=lambda c: c.name)
    }
    if args.cmd_name:
        info = schema.get(args.cmd_name)
        if not info:
            raise XaError(
                "unknown_command",
                f"commande inconnue: {args.cmd_name}",
                hint="lance `xa help` sans argument pour la liste",
            )
        return ok(info)
    return ok(schema)
