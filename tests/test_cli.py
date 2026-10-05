"""Tests for scripts/cli.py, the github-manager dispatcher used as the container and package entrypoint."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "cli.py"
FIXTURES = ROOT / "tests" / "fixtures"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, timeout=60, cwd=ROOT)


def load_cli():
    import importlib.util

    spec = importlib.util.spec_from_file_location("github_manager_cli", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_help_lists_every_subcommand():
    cli = load_cli()
    result = run("--help")
    assert result.returncode == 0
    assert result.stdout.startswith("usage: github-manager <subcommand>")
    assert list(cli.COMMANDS) == ["pr-queue", "iteration-report", "postmortem"]
    for name, (_, script, _) in cli.COMMANDS.items():
        assert f"  {name} " in result.stdout
        assert script in result.stdout


def test_every_subcommand_points_at_an_existing_script_and_answers_help():
    cli = load_cli()
    for name, (_, script, _) in cli.COMMANDS.items():
        assert cli.script_path(name).is_file(), name
        result = run(name, "--help")
        assert result.returncode == 0, (name, result.stderr)
        assert result.stdout.startswith(f"usage: {script}"), name


def test_every_skill_script_has_a_subcommand():
    cli = load_cli()
    covered = {cli.script_path(n).resolve() for n in cli.COMMANDS}
    scripts = {p.resolve() for p in cli.SKILLS.glob("*/scripts/[a-z]*.py")}
    assert scripts == covered


def test_help_subcommand_shows_the_script_help():
    result = run("help", "postmortem")
    assert result.returncode == 0
    assert "postmortem.py" in result.stdout


def test_unknown_subcommand_and_no_arguments_exit_2():
    result = run("no-such-command")
    assert result.returncode == 2
    assert "unknown subcommand" in result.stderr
    assert run().returncode == 2


def test_exit_code_and_arguments_pass_through():
    result = run("pr-queue", "--definitely-not-an-option")
    assert result.returncode == 2
    assert "usage: " in result.stderr


def test_pr_queue_through_the_dispatcher_keeps_exit_1_and_json():
    result = run("pr-queue", str(FIXTURES / "pr_queue"), "--json")
    assert result.returncode == 1
    assert json.loads(result.stdout)["summary"]["by_check"]["blocked-on-reviewer"] == [101]


def test_iteration_report_through_the_dispatcher():
    result = run("iteration-report", str(FIXTURES / "iteration"), "--from", "2026-09-14", "--to", "2026-09-25",
                 "--json")
    assert result.returncode == 0
    assert [r["number"] for r in json.loads(result.stdout)["carried_over"]] == [204, 205]


def test_postmortem_through_the_dispatcher():
    result = run("postmortem", str(FIXTURES / "postmortem"), "--issue", "412", "--redact")
    assert result.returncode == 0
    assert "# Postmortem:" in result.stdout and "octocat" not in result.stdout


def test_version_matches_every_version_field():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    plugin_json = ROOT / "plugins" / "github-manager" / ".claude-plugin" / "plugin.json"
    plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    expected = pyproject["project"]["version"]
    assert plugin["version"] == expected
    assert market["metadata"]["version"] == expected
    assert all(p["version"] == expected for p in market["plugins"])
    result = run("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"github-manager {expected}"


def test_cli_is_executable_with_a_shebang():
    assert CLI.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3")
    if os.name == "posix":
        assert os.access(CLI, os.X_OK)


def test_package_layout_finds_skills_next_to_the_module(tmp_path):
    """The wheel puts cli.py and skills/ side by side in github_manager_skills/; the dispatcher must find them."""
    import shutil

    pkg = tmp_path / "github_manager_skills"
    pkg.mkdir()
    shutil.copy(CLI, pkg / "cli.py")
    shutil.copytree(ROOT / "plugins" / "github-manager" / "skills", pkg / "skills")
    result = subprocess.run([sys.executable, str(pkg / "cli.py"), "pr-queue", "--help"], capture_output=True,
                            text=True, timeout=60, cwd=tmp_path)
    assert result.returncode == 0 and result.stdout.startswith("usage: pr_queue.py")
