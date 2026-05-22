"""Registre des commandes via decorator `@register`.

Chaque feature module importe `register` et l'utilise au-dessus de ses
fonctions `cmd_*`. L'import de `xa.features` (dans `cli.py`) déclenche
l'exécution des décorateurs et peuple `COMMANDS`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Command:
    name: str
    fn: Callable[[Any], dict]
    configure: Callable[..., None]
    description: str
    is_write: bool = False


COMMANDS: list[Command] = []


def register(
    name: str,
    *,
    configure: Callable[..., None] | None = None,
    is_write: bool = False,
) -> Callable:
    """Décorateur qui enregistre une commande dans le registre global.

    Le `description` est extrait de la première ligne du docstring.

    Args:
        name: nom de la sous-commande (ex: "search", "tweet").
        configure: callable qui prend un sous-parser argparse et y attache
                   les arguments. Peut être None si la commande n'a pas d'args.
        is_write: True si la commande modifie l'état du compte X.
                  Le verrou `--yes` est géré par le dispatcher dans
                  `cli.py:_dispatch` (qui injecte l'argument argparse et
                  vérifie sa présence avant d'appeler la commande).
    """

    def deco(fn):
        desc = (fn.__doc__ or "").strip().split("\n")[0]
        COMMANDS.append(
            Command(
                name=name,
                fn=fn,
                configure=configure or (lambda sp: None),
                description=desc,
                is_write=is_write,
            )
        )
        return fn

    return deco
