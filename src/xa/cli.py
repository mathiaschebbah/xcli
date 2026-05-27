"""Entry point CLI : construit le parser argparse à partir du registry.

Conventions :
- Tous les sous-parsers ont accès à `--human` (déplacé en début d'argv).
- Les commandes `is_write=True` reçoivent automatiquement `--yes` ; le
  dispatcher vérifie sa présence avant d'appeler la fonction métier.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import features  # noqa: F401 — déclenche tous les @register
from .core.errors import XaError
from .core.output import emit, err
from .core.registry import COMMANDS, Command
from .features._common import attach_yes_flag


def _build_subparser(sub, cmd: Command) -> argparse.ArgumentParser:
    sp = sub.add_parser(cmd.name, help=cmd.description)
    cmd.configure(sp)
    if cmd.is_write:
        attach_yes_flag(sp)
    sp.set_defaults(_cmd=cmd)
    return sp


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
        _build_subparser(sub, cmd)
    return p


def _dispatch(args) -> dict:
    """Vérifie le verrou --yes pour les writes, puis appelle la commande."""
    cmd: Command = args._cmd
    if cmd.is_write and not getattr(args, "yes", False):
        raise XaError(
            "confirmation_required",
            f"l'action '{cmd.name}' modifie ton compte X et requiert --yes",
            hint="ajoute --yes pour confirmer explicitement",
        )
    return cmd.fn(args)


def _force_utf8_stdio() -> None:
    """Force UTF-8 sur stdout/stderr.

    Sur Windows, le code page console par défaut (cp1252) corrompt les
    caractères accentués du JSON. `reconfigure` est dispo depuis Python 3.7
    et no-op sur les flux déjà configurés.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfig = getattr(stream, "reconfigure", None)
        if reconfig is not None:
            try:
                reconfig(encoding="utf-8")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    if argv is None:
        argv = sys.argv[1:]
    # Permet --human n'importe où dans argv (argparse exige avant la sous-cmd
    # par défaut).
    if "--human" in argv:
        argv = ["--human"] + [a for a in argv if a != "--human"]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = _dispatch(args)
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
