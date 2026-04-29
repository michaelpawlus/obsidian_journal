from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from obsidian_journal import cli, vault
from obsidian_journal.config import Config
from obsidian_journal.models import Frontmatter, SpecNote
from obsidian_journal.spec.synthesize import slug_for_title


SPEC_BODY_FIXTURE = """\
# oj spec Subcommand

## Why

- Specs currently bypass the writer-of-record.

## Scope

- Single new `oj spec` command.

## Architecture / Touch Points

- `src/obsidian_journal/cli.py`
- `src/obsidian_journal/spec/synthesize.py`

## Acceptance Criteria

- [ ] `oj --json spec -q "..."` returns the v0.3 payload.
- [ ] Frontmatter includes baseline tags.

## Open Questions

- Folder routing — flat or nested?

## Follow-ups

- `oj spec edit` for refinements.
"""


# --------------------------------------------------------------------------------------
# Pure-unit tests (no CLI / API).
# --------------------------------------------------------------------------------------


def test_slug_for_title_appends_spec_suffix():
    assert slug_for_title("oj spec Subcommand") == "oj-spec-subcommand-spec"


def test_slug_for_title_keeps_existing_spec_suffix():
    assert slug_for_title("Conductor Doctor Spec") == "conductor-doctor-spec"


def test_slug_for_title_punctuation_squashed():
    assert (
        slug_for_title("Conductor Doctor: Check Subcommands")
        == "conductor-doctor-check-subcommands-spec"
    )


def test_write_spec_collision_appends_suffix(tmp_path: Path):
    cfg = Config(vault_path=tmp_path, anthropic_api_key="test-key")
    front = Frontmatter(
        date="2026-04-28",
        tags=["project-idea", "spec", "active"],
        extra={"status": "planning", "complexity": "M", "priority": "medium"},
    )
    spec = SpecNote(
        title="oj spec Subcommand",
        body="body content",
        frontmatter=front,
        folder="Project Ideas",
        complexity="M",
        priority="medium",
        status="planning",
    )

    p1 = vault.write_spec(cfg, spec, "oj-spec-subcommand-spec")
    p2 = vault.write_spec(cfg, spec, "oj-spec-subcommand-spec")
    p3 = vault.write_spec(cfg, spec, "oj-spec-subcommand-spec")

    assert p1.name == "oj-spec-subcommand-spec.md"
    assert p2.name == "oj-spec-subcommand-spec-2.md"
    assert p3.name == "oj-spec-subcommand-spec-3.md"
    assert (tmp_path / "Project Ideas").is_dir()


# --------------------------------------------------------------------------------------
# CLI smoke tests.
# --------------------------------------------------------------------------------------


@pytest.fixture
def vault_path(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def env(monkeypatch, vault_path):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    cli.json_mode = False


def _patched_anthropic(body_text: str = SPEC_BODY_FIXTURE) -> MagicMock:
    fake_body = MagicMock()
    fake_body.content = [MagicMock(text=body_text)]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_body
    return fake_client


def test_spec_json_no_quick_exits_2(runner: CliRunner):
    result = runner.invoke(cli.app, ["--json", "spec"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"] == "--quick is required when using --json"
    assert payload["code"] == 2
    assert payload["_oj_version"] == "0.3"


def test_spec_json_quick_writes_and_emits_payload(
    runner: CliRunner, vault_path: Path
):
    fake_client = _patched_anthropic()
    with patch(
        "obsidian_journal.spec.synthesize.Anthropic",
        return_value=fake_client,
    ):
        result = runner.invoke(
            cli.app,
            [
                "--json",
                "spec",
                "-q",
                "Add a doctor subcommand to conductor.",
                "--complexity",
                "M",
                "--priority",
                "high",
                "--tag",
                "oj,conductor",
                "--source",
                "code-daily 2026-04-28",
            ],
        )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    payload = json.loads(result.stdout)

    assert payload["_oj_version"] == "0.3"
    assert payload["folder"] == "Project Ideas"
    assert payload["title"] == "oj spec Subcommand"
    assert payload["path"] == "Project Ideas/oj-spec-subcommand-spec.md"
    assert payload["absolute_path"].endswith("oj-spec-subcommand-spec.md")

    front = payload["frontmatter"]
    # Baseline tags always present, in order, plus user tags.
    assert front["tags"][0] == "project-idea"
    assert front["tags"][1] == "spec"
    assert front["tags"][-1] == "active"
    assert "oj" in front["tags"]
    assert "conductor" in front["tags"]
    # Spec-specific frontmatter.
    assert front["status"] == "planning"
    assert front["complexity"] == "M"
    assert front["priority"] == "high"
    assert front["source"] == "code-daily 2026-04-28"
    # Six required sections in body.
    body = payload["body"]
    for heading in (
        "## Why",
        "## Scope",
        "## Architecture / Touch Points",
        "## Acceptance Criteria",
        "## Open Questions",
        "## Follow-ups",
    ):
        assert heading in body, f"missing heading {heading!r}"
    # H1 stripped from body.
    assert not body.lstrip().startswith("# ")

    # File actually exists on disk with frontmatter.
    on_disk = (vault_path / payload["path"]).read_text(encoding="utf-8")
    assert on_disk.startswith("---")
    assert "tags:" in on_disk
    assert "complexity: M" in on_disk
    assert "priority: high" in on_disk

    # Stderr silent in --json mode.
    assert result.stderr == ""
