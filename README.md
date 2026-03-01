# Obsidian Journal (`oj`)

An agentic CLI that captures reflections through guided conversation with Claude, synthesizes them into well-structured Markdown notes, and saves them to your Obsidian vault.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Create a `.env` file or use `oj config set`:

```bash
oj config set OBSIDIAN_VAULT_PATH /path/to/your/vault
oj config set ANTHROPIC_API_KEY sk-ant-...
```

Optional settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `OJ_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `OJ_MAX_ROUNDS` | `4` | Max conversation rounds |
| `OJ_LOCATION_LAT` | *(none)* | Latitude for weather forecasts (enables weather-aware planning) |
| `OJ_LOCATION_LON` | *(none)* | Longitude for weather forecasts |
| `OJ_DAILY_NOTES_FOLDER` | `Daily Notes` | Vault folder for daily notes |

View current config:

```bash
oj config show
```

## Usage

### Journal capture

Start a guided reflection session:

```bash
oj journal                     # interactive type picker
oj journal -t end-of-day       # skip the picker
oj journal -t meeting          # debrief a meeting
oj journal -t reading          # capture reading notes
```

Quick capture (skip the conversation, go straight to synthesis):

```bash
oj journal -q "Had a great 1:1 with my manager about career growth"
oj journal -t meeting -q "Standup: discussed blockers on the API migration"
```

### Daily planning

Create a structured, time-blocked plan for your day:

```bash
oj plan                        # interactive planning conversation
oj plan -q "standup at 9, write report, gym, review PRs"  # quick plan
```

The plan command:
- Gathers your tasks, meetings, and priorities through a guided conversation
- Fetches today's weather (if location is configured) and suggests optimal outdoor time
- Produces a time-blocked schedule with priority markers
- Pushes overflow items to tomorrow when the day is overloaded
- Saves to your daily note (`Daily Notes/YYYY-MM-DD.md`)

To enable weather-aware planning, set your coordinates (find them by right-clicking your city on Google Maps):

```bash
oj config set OJ_LOCATION_LAT 41.8781
oj config set OJ_LOCATION_LON -87.6298
```

### List recent notes

```bash
oj list                        # show 10 most recent journal notes
oj list -n 5                   # limit to 5
oj list -f "Daily Notes"       # list from a different folder
```

### Organize your vault

```bash
oj organize links              # find wikilink opportunities
oj organize links --apply      # apply suggested links
oj organize frontmatter        # standardize YAML frontmatter
oj organize structure          # suggest folder reorganization
```

Add `--deep` to `links` or `structure` for Claude-powered semantic analysis.

## How it works

1. **Capture** — Claude guides you through a short reflection conversation tailored to the type (end-of-day, project retro, podcast, meeting, reading, or free-form).
2. **Synthesize** — Your conversation is sent to Claude to produce a structured note with title, tags, related notes, and a clean body.
3. **Save** — The note is written to your vault with YAML frontmatter, ready for Obsidian.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Roadmap

- [ ] More test coverage (CLI integration tests, synthesize tests)
- [ ] `oj stats` — summary of journal activity over time
- [ ] `--tags` flag for `oj journal` to pre-set tags
- [x] Daily note integration (`oj plan` — structured daily planning with weather)
- [ ] Search and export commands
- [ ] Template support for custom note structures
