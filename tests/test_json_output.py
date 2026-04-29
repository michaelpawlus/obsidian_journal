from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from obsidian_journal import cli


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    journal = tmp_path / "Journal"
    journal.mkdir()
    (journal / "2026-04-25 First note.md").write_text(
        "---\ndate: '2026-04-25'\ntype: end-of-day\ntags:\n  - daily\n---\nFirst body.\n"
    )
    (journal / "2026-04-26 Second note.md").write_text(
        "---\ndate: '2026-04-26'\ntype: meeting\ntags:\n  - work\n---\nSecond body.\n"
    )
    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def env(monkeypatch, vault):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # Ensure cli json_mode resets between tests.
    cli.json_mode = False


def test_list_json_emits_valid_json_with_version(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "list"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["_oj_version"] == "0.3"
    assert payload["folder"] == "Journal"
    assert payload["count"] == 2
    items = payload["items"]
    assert len(items) == 2
    for item in items:
        assert "path" in item
        assert "title" in item
        assert "modified_at" in item
        assert "tags" in item
    # Sorted reverse-by-filename: most recent first.
    assert items[0]["path"].endswith("2026-04-26 Second note.md")


def test_list_json_silent_stderr_on_success(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "list"])
    assert result.exit_code == 0
    assert result.stderr == ""


def test_query_json_filters_and_versions(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "query", "--type", "meeting"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["_oj_version"] == "0.3"
    assert payload["count"] == 1
    assert payload["items"][0]["frontmatter"]["type"] == "meeting"


def test_get_json_returns_full_note(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "get", "First note"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["_oj_version"] == "0.3"
    assert payload["title"] == "2026-04-25 First note"
    assert payload["body"].startswith("First body")
    assert payload["path"].endswith("First note.md")


def test_get_json_not_found_exits_2(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "get", "nonexistent"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"] == "Note not found"
    assert payload["code"] == 2


def test_config_show_json(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "config", "show"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["_oj_version"] == "0.3"
    assert "vault_path" in payload
    assert "model" in payload


def test_journal_json_no_quick_exits_2(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "journal"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert "error" in payload
    assert payload["code"] == 2
    assert payload["_oj_version"] == "0.3"


def test_journal_json_quick_emits_spec_keys(runner: CliRunner, monkeypatch):
    fake_body = MagicMock()
    fake_body.content = [MagicMock(text="A reflection body.")]
    fake_title = MagicMock()
    fake_title.content = [MagicMock(text="Career growth chat")]

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [fake_body, fake_title]

    with patch(
        "obsidian_journal.journal.synthesize.Anthropic",
        return_value=fake_client,
    ):
        result = runner.invoke(
            cli.app,
            ["--json", "journal", "-t", "end-of-day", "-q", "had a great 1:1"],
        )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    payload = json.loads(result.stdout)
    assert payload["_oj_version"] == "0.3"
    for key in ("path", "title", "tags", "frontmatter"):
        assert key in payload, f"missing {key} in {payload}"
    assert "Career growth chat" in payload["title"]
    assert payload["frontmatter"]["type"] == "end-of-day"
    assert "journal/end-of-day" in payload["tags"]
    # Stderr is silent in --json mode.
    assert result.stderr == ""


def test_plan_json_no_quick_exits_2(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "plan"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["code"] == 2
    assert payload["_oj_version"] == "0.3"


def test_plan_json_quick_emits_spec_keys(runner: CliRunner, monkeypatch):
    plan_md = (
        "## Plan\n\n"
        "### Schedule\n\n"
        "- **08:30 - 09:00** | Standup [HIGH]\n"
        "- **09:00 - 10:30** | Deep work [MED]\n"
        "- **12:00 - 13:00** | Lunch [LOW]\n"
    )
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(text=plan_md)]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_resp

    with patch(
        "obsidian_journal.plan.synthesize.Anthropic",
        return_value=fake_client,
    ):
        result = runner.invoke(
            cli.app,
            ["--json", "plan", "-q", "standup, deep work, lunch"],
        )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    payload = json.loads(result.stdout)
    assert payload["_oj_version"] == "0.3"
    for key in ("path", "frontmatter", "blocks", "weather"):
        assert key in payload, f"missing {key} in {payload}"
    assert payload["weather"] is None  # no location set
    assert len(payload["blocks"]) == 3
    assert payload["blocks"][0] == {
        "start": "08:30",
        "end": "09:00",
        "task": "Standup",
        "priority": "HIGH",
    }
    assert result.stderr == ""


def test_organize_links_json(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "organize", "links"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["_oj_version"] == "0.3"
    assert "applied" in payload
    assert "suggestions" in payload
