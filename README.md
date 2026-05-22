# xa — CLI agent-native pour X.com (Twitter)

Une commande `xa` qui parle directement à l'API privée de x.com (Twitter)
en réutilisant ta session Chrome. Sortie JSON, conçue pour être pilotée
par un agent.

## Installation

```bash
git clone <URL_DU_REPO> ~/Desktop/Projets/xcli
cd ~/Desktop/Projets/xcli
./install.sh
```

`install.sh` exige `uv` ([installation](https://docs.astral.sh/uv/getting-started/installation/))
et Chrome (ou Brave/Edge/Chromium) connecté sur https://x.com. Il :

1. Synchronise l'environnement Python (`uv sync`, Python 3.13)
2. Pose un wrapper `xa` dans `~/.local/bin/`
3. Installe le skill Claude Code dans `~/.claude/skills/x-twitter/`

Si `~/.local/bin` n'est pas dans ton `PATH`, l'install te le dit.

## Première utilisation

```bash
xa auth-init       # extrait les cookies X depuis Chrome
xa auth-status     # vérifie que la session est valide
xa whoami          # JSON du compte connecté
```

## Utilisation

Toutes les commandes sortent un JSON `{ok, data, next_cursor?, count?}`.
Ajoute `--human` n'importe où pour une sortie lisible.

```bash
xa --help                       # liste des commandes
xa help                         # schéma JSON des commandes (machine-readable)
xa search "X" --limit 50        # search tweets
xa user @screen_name            # profil
xa tweets @screen_name          # tweets d'un compte
xa thread <tweet_id>            # fil de conversation
xa following @screen_name       # qui ce compte suit
xa post "hello" --yes           # écriture (verrouillée par --yes)
```

Voir [`.claude/skills/x-twitter/SKILL.md`](.claude/skills/x-twitter/SKILL.md)
pour la documentation complète orientée agent (toutes les commandes,
recipes, troubleshooting, optimisation tokens).

## Désinstallation

```bash
./install.sh --uninstall
```

## Licence

MIT — voir [LICENSE](LICENSE).
