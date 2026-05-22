---
name: x-twitter
description: >
  Use this skill whenever the user wants to interact with X (Twitter): search
  for tweets, look up a profile, get someone's followers/following, read a
  thread, fetch a specific tweet, see trends. Trigger phrases include "search
  on X / Twitter", "find tweets about…", "what's @someone tweeting", "look up
  X profile", "fetch this tweet", "get the thread on…", "trending on X".
  Also trigger on French equivalents: "cherche sur X / Twitter", "trouve des
  tweets", "qui est @X", "donne-moi le profil de @X", "récupère ce tweet",
  "qu'est-ce qui buzz sur Twitter". The skill exposes a CLI `xa` that wraps
  X's private GraphQL API using the user's logged-in Chrome session.
  Also valid for write actions on X (post, reply, like, follow…) when the
  user explicitly asks — those require `--yes` to confirm.
---

# X (Twitter) via `xa` CLI

The user has a CLI named `xa` installed via the `xcli` project. It wraps the
private GraphQL API of x.com and reuses the cookies of the Chrome browser
where the user is logged in.

If `xa` is not on the PATH, the project has not been installed. Tell the user
to run `./install.sh` from the cloned `xcli` repo.

## When to use this skill

Use it for **anything related to X (Twitter)**: search, profiles, threads,
trends, posting, etc. Don't try to build an alternative; `xa` is faster and
more reliable than scraping the web.

Don't use it for:
- Generic web search (use WebSearch instead)
- LinkedIn, Mastodon, BlueSky, Instagram (not supported)

## Output contract (machine-readable)

`xa` always outputs ONE JSON document on stdout. Format:

```json
{ "ok": true, "data": <result>, "next_cursor": "...", "count": N }
```

On error:

```json
{ "ok": false, "error": "<code>", "message": "...", "hint": "..." }
```

Logs (TID init, retries) go to stderr — stdout stays pure for piping.

To get human-readable output, add `--human` anywhere in the command.

## Discovery

```bash
xa --help                        # liste les commandes
xa help                          # JSON schema de toutes les commandes
xa help search                   # détail d'une commande
xa ops --filter Tweet            # liste les ops GraphQL disponibles (158)
```

## Most useful commands

### Auth (one-time)
```bash
xa auth-init                     # extrait cookies de Chrome → ~/.config/xa/
xa auth-status                   # vérifie la session
xa whoami                        # logged-in user
```

If `auth_required` error: tell the user to run `xa auth-init` (one-time setup
per session refresh, requires Chrome to be logged in on x.com).

### Reads (default, no --yes required)
```bash
xa search "QUERY" --product Latest|Top|Media|People --limit 50
xa user SCREEN_NAME
xa tweet TWEET_ID
xa thread TWEET_ID
xa tweets SCREEN_NAME --limit 100
xa replies SCREEN_NAME --limit 50
xa media SCREEN_NAME --limit 30
xa likes SCREEN_NAME --limit 50
xa following SCREEN_NAME --limit 200
xa followers SCREEN_NAME --limit 200
xa trends
```

All paginated commands take `--limit N` (default 50) and `--cursor C` to
resume from a previous run's `next_cursor`.

### Token optimization
Use `--fields a,b,c` to reduce JSON size. Available fields:
- Tweets: `id, created_at, author, author_name, text, lang,
  favorite_count, retweet_count, reply_count, quote_count, view_count,
  is_reply, in_reply_to_status_id, url`
- Users: `rest_id, screen_name, name, description, followers_count,
  friends_count, verified, url`

Example for token-efficient search:
```bash
xa search "anthropic claude" --product Latest --limit 100 --fields id,author,text
```

### Writes (require --yes EACH TIME)
```bash
xa post "TEXT" --yes
xa reply TWEET_ID "TEXT" --yes
xa delete-tweet TWEET_ID --yes
xa like TWEET_ID --yes / xa unlike TWEET_ID --yes
xa retweet TWEET_ID --yes / xa unretweet TWEET_ID --yes
xa bookmark TWEET_ID --yes / xa unbookmark TWEET_ID --yes
xa follow SCREEN_NAME --yes / xa unfollow SCREEN_NAME --yes
```

**Important**: ALWAYS confirm with the user before running a write
command. Writes are visible publicly and affect the user's account
reputation. Never batch-like, batch-follow, or auto-DM.

### Escape hatch (any of 158 GraphQL ops)
```bash
xa ops --filter SearchTimeline       # list ops in the catalog
xa raw <OpName> --vars '{"k":"v"}'   # any read op from the catalog
xa raw <OpName> --vars '{...}' --method POST --yes   # any mutation
```

## Recipes

### "What's everyone saying about X?"
```bash
xa search "X" --product Latest --limit 50 --fields id,author,text,favorite_count,view_count
```
Then summarize the tweets.

### "Show me @user's recent activity"
```bash
xa user USER --fields screen_name,description,followers_count
xa tweets USER --limit 20 --fields id,created_at,text,favorite_count
```

### "Get the thread on this tweet URL"
Extract the tweet_id (last numeric segment of `https://x.com/.../status/<id>`).
```bash
xa thread <id> --fields id,author,text
```

### Pagination loop
```bash
cursor=""
while :; do
  out=$(xa search "X" --limit 100 ${cursor:+--cursor "$cursor"})
  echo "$out" | jq '.data[]'
  cursor=$(echo "$out" | jq -r .next_cursor)
  [ "$cursor" = "null" -o -z "$cursor" ] && break
done
```

## Rate limits & hygiene

X enforces ~50–250 requests per 15min window per endpoint. `xa` retries on
429 with exponential backoff. For massive scrapes:
- Use `--limit` to cap rows
- Insert `sleep 2` between heavy commands
- Switch to a burner account if scraping at scale

Never use this for mass-following, mass-DM, or unsolicited bulk posting —
the account will be flagged or suspended.

## Troubleshooting

| Error code | Cause | Fix |
|---|---|---|
| `auth_required` | no cookies saved | `xa auth-init` |
| `session_invalid` | cookies expired | log in again in Chrome, then `xa auth-init` |
| `user_not_found` | typo or banned/protected | check the screen_name |
| `confirmation_required` | tried a write without `--yes` | re-run with `--yes` |
| `unknown_op` | op not in catalog | `xa harvest-ops` to refresh, or `xa ops --filter <name>` |
| `http_error: HTTP 404` | stale queryId (X updated its API) | `xa harvest-ops` to regenerate the catalog |
| `http_error: HTTP 403` | `x-client-transaction-id` algo broken or cookies bad | check `x-client-transaction-id` lib installed; if OK, re-init auth |

### When ops fail repeatedly (X updated its client)
```bash
xa harvest-ops               # regenerates x_ops.json from the current JS bundles
```

### Inspect cookies for auth debug
```bash
xa cookies x.com             # values masked
xa cookies x.com --reveal    # values in clear (useful for curl)
xa cookies x.com --format header --reveal   # ready for `curl -H "Cookie: ..."`
```
