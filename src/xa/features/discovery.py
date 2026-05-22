"""Découverte : `xa trends`, `xa ops [--filter]`, `xa help [cmd]`."""

from __future__ import annotations

import argparse

from ..core.errors import XaError
from ..core.ops import load_ops
from ..core.output import ok
from ..core.registry import COMMANDS, Command, register
from ._common import get_client


# Flag global accepté par toutes les commandes via cli.py (hoist de --human
# vers le début d'argv). Documenté explicitement dans tous les schemas.
_GLOBAL_FLAGS = [
    {
        "name": "human",
        "kind": "option",
        "flags": ["--human"],
        "required": False,
        "default": False,
        "help": "sortie lisible humain (sinon JSON)",
    }
]


def _args_ops(sp):
    sp.add_argument("--filter", help="filtre les ops dont le nom contient X")


def _args_help(sp):
    sp.add_argument("cmd_name", nargs="?", help="nom d'une commande spécifique")


@register("trends")
def cmd_trends(args) -> dict:
    """Tendances X récentes."""
    client = get_client()
    data = client.call("TrendHistory", {})
    return ok(data.get("data") or data)


@register("ops", configure=_args_ops)
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


@register("help", configure=_args_help)
def cmd_help(args) -> dict:
    """Schéma machine-readable de toutes les commandes (ou détail d'une seule).

    Sans argument : retourne un index `{shape: "index", commands: {...}}`.
    Avec un nom de commande : introspecte le subparser et retourne
    `{shape: "command", ...}` avec la signature complète.
    """
    if args.cmd_name:
        cmd = next((c for c in COMMANDS if c.name == args.cmd_name), None)
        if not cmd:
            raise XaError(
                "unknown_command",
                f"commande inconnue: {args.cmd_name}",
                hint="lance `xa help` sans argument pour la liste",
            )
        return ok(_describe_command(cmd))

    return ok({
        "shape": "index",
        "commands": {
            c.name: {
                "description": c.description,
                "type": "write" if c.is_write else "read",
            }
            for c in sorted(COMMANDS, key=lambda c: c.name)
        },
        "global_flags": _GLOBAL_FLAGS,
        "hint": "appelle `xa help <cmd>` pour le schéma détaillé d'une commande",
    })


def _describe_command(cmd: Command) -> dict:
    """Construit un schéma JSON détaillé d'une commande via introspection."""
    sp = argparse.ArgumentParser(prog=f"xa {cmd.name}", add_help=False)
    cmd.configure(sp)
    if cmd.is_write:
        sp.add_argument(
            "--yes",
            action="store_true",
            help="confirme explicitement cette action visible publiquement",
        )

    args_schema = []
    for action in sp._actions:  # noqa: SLF001 — API argparse stable
        if action.dest == "help":
            continue
        info = {
            "name": action.dest,
            "kind": "positional" if not action.option_strings else "option",
            "flags": list(action.option_strings),
            "required": bool(action.required),
            "help": action.help,
        }
        if action.choices:
            info["choices"] = list(action.choices)
        if action.default is not None and action.default is not argparse.SUPPRESS:
            info["default"] = action.default
        if action.type:
            info["type"] = getattr(action.type, "__name__", str(action.type))
        if action.nargs is not None:
            info["nargs"] = action.nargs
        args_schema.append(info)

    schema = {
        "shape": "command",
        "name": cmd.name,
        "description": cmd.description,
        "type": "write" if cmd.is_write else "read",
        "arguments": args_schema,
        "global_flags": _GLOBAL_FLAGS,
    }
    # raw est registered is_write=False car le type d'op est résolu à
    # l'exécution. On signale à l'agent que --yes est requis si la cible
    # est une mutation.
    if cmd.name == "raw":
        schema["note"] = (
            "Si l'op ciblée est une mutation (operationType == 'mutation'), "
            "--yes est obligatoire — sinon `confirmation_required` est levé."
        )
    return schema
