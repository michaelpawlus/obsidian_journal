# Claude Code Notes — `obsidian_journal` (`oj`)

## Persona — `oj` is the household's Obsidian writer-of-record

Any agent that wants to land a note in the user's Obsidian vault should call **`oj`**, never write to `$OBSIDIAN_VAULT_PATH` directly. `oj` owns:

- Frontmatter (`date`, `type`, `tags`, `related`)
- Folder routing (`Journal/`, `Daily Notes/`, etc.)
- Filename conventions (`YYYY-MM-DD <slug>.md`)
- The journal/plan synthesis prompts

If you need a different folder or note type, **add a command to `oj` first** — don't side-channel into the vault. This keeps every entrypoint into the vault going through one schema.

This is the one personal-use project that is **API-driven** (uses `ANTHROPIC_API_KEY` via the `anthropic` SDK, not Claude Code) so it can run unattended from cron and from other CLIs. That's intentional — see "Non-goal" below.

## Running tests

```bash
.venv/bin/pytest
```

(There is no system-wide `pytest`.) The CLI is installed via `pip install -e .`; invoke as `oj`, never as `python -m obsidian_journal`.

## Available commands

| Command | Purpose | Reads/Writes |
|---|---|---|
| `oj journal [-t TYPE] [-q TEXT] [--json]` | Guided reflection capture | Writes `Journal/YYYY-MM-DD <title>.md` |
| `oj plan [-q TEXT] [--json]` | Time-blocked daily plan w/ optional weather | Writes `Daily Notes/YYYY-MM-DD.md` |
| `oj list [-n N] [-f FOLDER] [--json]` | Recent notes in a folder | Read |
| `oj query [--type T] [--tags …] [--since …] [--until …] [--folder …] [--search …] [-n N] [--json]` | Structured search across the vault | Read |
| `oj get TITLE [--json]` | Fetch a single note by title (exact, then partial) | Read |
| `oj organize {links,frontmatter,structure} [--apply] [--deep] [--json]` | Vault hygiene — preview by default | Read (preview) / write (`--apply`) |
| `oj config show [--json]` | Resolved config | Read |
| `oj config set KEY VALUE` | Persist a key in `.env` | Write |

`ReflectionType` values for `-t`: `end-of-day`, `end-of-project`, `podcast`, `meeting`, `reading`, `free-form`.

## Always-callable agent surface

- Pass `--json` (top-level flag, before the subcommand: `oj --json list`) on **every** command for structured output.
- In `--json` mode, `journal` and `plan` **require** `-q TEXT` — interactive prompts are disabled and exit `2` with `{"error": "--quick is required when using --json", "code": 2}`.
- Stdout = JSON only. Stderr = silent on success, human errors otherwise.
- Exit codes: `0` ok, `1` general error (e.g. config/env missing), `2` bad input / not found.

## Environment

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OBSIDIAN_VAULT_PATH` | yes | — | Set globally in `~/.bashrc` |
| `ANTHROPIC_API_KEY` | yes | — | Required even for read-only commands today (loaded eagerly) |
| `OJ_MODEL` | no | `claude-sonnet-4-20250514` | |
| `OJ_MAX_ROUNDS` | no | `4` | Conversation rounds for `journal` |
| `OJ_LOCATION_LAT` / `OJ_LOCATION_LON` | no | unset | Enables weather-aware planning |
| `OJ_DAILY_NOTES_FOLDER` | no | `Daily Notes` | |

## JSON contract (v0.2)

Every JSON object includes `"_oj_version": "0.2"`. Bump this in `output.py:OJ_VERSION` when the shape changes; downstream callers should pin against it.

```jsonc
// oj --json journal -t end-of-day -q "..."
{
  "_oj_version": "0.2",
  "path": "Journal/2026-04-27 Career growth chat.md",  // relative to vault
  "absolute_path": "/.../Obsidian Vault/Journal/...md",
  "title": "2026-04-27 Career growth chat",
  "tags": ["journal/end-of-day"],
  "frontmatter": {"date": "2026-04-27", "type": "end-of-day", "tags": [...], "related": [...]},
  "related": ["Career planning"],
  "folder": "Journal",
  "body": "..."  // synthesized markdown
}

// oj --json plan -q "..."
{
  "_oj_version": "0.2",
  "path": "Daily Notes/2026-04-27.md",
  "absolute_path": "...",
  "date": "2026-04-27",
  "frontmatter": {"date": "...", "type": "daily-note", "tags": ["daily"]},
  "blocks": [
    {"start": "08:30", "end": "09:00", "task": "Standup", "priority": "HIGH"}
  ],
  "markdown": "## Plan\n\n### Schedule\n...",  // raw synthesized plan, fall back if blocks is []
  "weather": {"temperature_high_f": 72.0, "summary": "...", ...} | null
}

// oj --json list  (and oj --json query)
{
  "_oj_version": "0.2",
  "folder": "Journal",         // list only
  "count": 12,
  "items": [
    {"path": "...", "title": "...", "modified_at": "2026-04-27T13:00:00+00:00",
     "tags": [...], "date": "...", "type": "..."}
  ]
}

// oj --json get TITLE  →  full Note dict (path, title, folder, filename, frontmatter, body, modified_at)
// oj --json config show  →  {vault_path, model, max_rounds, location_lat/lon, daily_notes_folder, api_key (masked)}
// oj --json organize {links|frontmatter|structure}  →  {applied: int, suggestions: [...]}
// errors  →  {"_oj_version": "0.2", "error": "...", "code": 1|2}
```

Lists are wrapped (`{items: [...]}`) rather than emitted as bare arrays so every payload has `_oj_version` for shape pinning.

## Cross-project usage examples

### `chief-of-staff` synthesizes a plan and reads the result back

```bash
out=$(oj --json plan -q "9am standup, deep work on auth migration, gym at 5, dinner at 7")
echo "$out" | jq -r '.path'           # → "Daily Notes/2026-04-27.md"
echo "$out" | jq '.blocks | length'   # → 4
```

### `code-daily` captures a reading-quest completion

```bash
oj --json journal -t reading \
  -q "Finished the LangGraph paper. Key takeaway: stateful agents need …" \
  | jq -r '.path'
```

Use this from a quest-completion hook so the user's read history flows into the vault next to manual journal entries.

### `workout-app` logs an end-of-day reflection after a long run

```bash
oj --json journal -t end-of-day \
  -q "10mi long run, felt strong miles 1-7, GI distress mile 8 …" \
  | jq -r '.path'
```

## What `oj` is **not**

- **Not** a vault search engine for fuzzy/semantic queries — `query` is structured-filter only. Heavy retrieval should live in a future `oj search` command, not in callers.
- **Not** a Claude-Code-driven agent. The synthesis happens via the `anthropic` SDK so this works headlessly from cron. A Claude-Code mode is a roadmap item once a second user touches the tool.
- **Not** a vault layout enforcer. File layout is the user's; this writes into existing folders.

## Touch-point map

- `src/obsidian_journal/cli.py` — Typer app. All commands; `--json` is a top-level callback flag setting `cli.json_mode`.
- `src/obsidian_journal/output.py` — `emit_json` / `emit_error` / `OJ_VERSION`. The single place all JSON leaves the process.
- `src/obsidian_journal/models.py` — `Note`, `Frontmatter`, `ReflectionType`, `WeatherInfo`. `Note.to_summary_dict()` is the slim `list` shape.
- `src/obsidian_journal/vault.py` — read/write/search. Populates `Note.path` and `Note.modified_at`.
- `src/obsidian_journal/journal/synthesize.py` — Anthropic call for journal notes.
- `src/obsidian_journal/plan/synthesize.py` — Anthropic call for plans.
- `src/obsidian_journal/plan/parse.py` — block parser for `--json` plan output.

## Roadmap

See `README.md` "Roadmap" section. Anything that touches the JSON shape needs a `_oj_version` bump.
