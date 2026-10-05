#!/usr/bin/env python3
"""github-manager: one command for the github-manager skill scripts.

    github-manager <subcommand> [args]       run one skill script with the given arguments
    github-manager <subcommand> --help       that script's own help
    github-manager --help                    list the subcommands

Each subcommand runs plugins/github-manager/skills/<skill>/scripts/<script>.py unchanged, in a child process with
the same Python, stdin, stdout, stderr and exit code. Standard library only. This is the entrypoint of the
container image ghcr.io/basitalisandhu/github-manager-skills and of the github-manager-skills Python package.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__version__ = "0.1.2"

PROG = "github-manager"
HERE = Path(__file__).resolve().parent
# In a checkout or the container image the skills sit at <root>/plugins/github-manager/skills; in the installed
# Python package they sit next to this file, at github_manager_skills/skills.
SKILLS = next(
    (p for p in (HERE.parent / "plugins" / "github-manager" / "skills", HERE / "skills") if p.is_dir()),
    HERE.parent / "plugins" / "github-manager" / "skills",
)

# subcommand: (skill directory, script, one-line summary)
COMMANDS: dict[str, tuple[str, str, str]] = {
    "pr-queue": (
        "pr-queue-digest",
        "pr_queue.py",
        "Stuck PRs, review queue per reviewer and next actions, each citing its PR",
    ),
    "iteration-report": (
        "iteration-report",
        "iteration_report.py",
        "Shipped, carried over, opened, cycle time and review turnaround for a window",
    ),
    "postmortem": (
        "incident-postmortem-timeline",
        "postmortem.py",
        "Blameless incident timeline and postmortem skeleton from an issue export",
    ),
}


def script_path(name: str) -> Path:
    skill, script, _ = COMMANDS[name]
    return SKILLS / skill / "scripts" / script


def usage() -> str:
    width = max(len(n) for n in COMMANDS)
    lines = [
        f"usage: {PROG} <subcommand> [args]",
        "",
        f"Runs one of the github-manager skill scripts over saved GitHub exports (no network). "
        f"Use '{PROG} <subcommand> --help' for its options.",
        "",
        "subcommands:",
    ]
    lines += [f"  {n.ljust(width)}  {h} ({script})" for n, (_, script, h) in COMMANDS.items()]
    lines += ["", "options:", "  -h, --help     show this help and exit", "  --version      show the version and exit"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(usage(), file=sys.stderr)
        return 2
    first, rest = args[0], args[1:]
    if first in ("-h", "--help", "help") and not rest:
        print(usage())
        return 0
    if first == "help":
        first, rest = rest[0], ["--help"]
    if first == "--version":
        print(f"{PROG} {__version__}")
        return 0
    if first not in COMMANDS:
        print(f"{PROG}: unknown subcommand {first!r}\n\n{usage()}", file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(script_path(first)), *rest])


if __name__ == "__main__":
    sys.exit(main())
