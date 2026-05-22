"""Entry point CLI : construit le parser argparse à partir du registry."""

from __future__ import annotations

import argparse
import json
import sys

from . import features  # noqa: F401 — déclenche tous les @register
from .core.errors import XaError
from .core.output import emit, err
from .core.registry import COMMANDS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="xa",
        description="CLI agent-native pour X.com (Twitter) — JSON-first.",
    )
    p.add_argument(
        "--human",
        action="store_true",
        help="sortie lisible humain (sinon JSON)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    for cmd in sorted(COMMANDS, key=lambda c: c.name):
        sp = sub.add_parser(cmd.name, help=cmd.description)
        cmd.configure(sp)
        sp.set_defaults(func=cmd.fn, _is_write=cmd.is_write)
    return p


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Permet --human n'importe où dans argv (argparse exige avant la sous-cmd
    # par défaut).
    if "--human" in argv:
        argv = ["--human"] + [a for a in argv if a != "--human"]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.func(args)
    except XaError as e:
        payload = err(e.code, e.message, hint=e.hint, **e.extras)
    except json.JSONDecodeError as e:
        payload = err("invalid_json", f"--vars n'est pas du JSON: {e}")
    except KeyboardInterrupt:
        payload = err("interrupted", "interrompu par l'utilisateur")
    except Exception as e:  # noqa: BLE001 — on veut catcher tout pour JSON propre
        payload = err("internal_error", f"{type(e).__name__}: {e}")
    return emit(payload, human=getattr(args, "human", False))


def cli() -> int:
    """Entry point exposé dans pyproject.toml comme `xa = "xa.cli:cli"`."""
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(cli())
