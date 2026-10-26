"""Seeded fuzz tests: mutated exports must give exit 0, 1 or 2, never a traceback.

Each case copies a committed fixture folder, then rewrites one or more of its JSON files with a seeded random mutation
(a value swapped for another type, a key dropped, a list emptied or wrapped, a time made nonsense, the whole file
truncated). The script must either read it (exit 0 or 1) or reject it with exit 2 and a message on stderr. Any other
exception fails the test with the seed, so a failure can be replayed with FUZZ_SEED=<seed>. Standard library only.
"""
from __future__ import annotations

import json
import os
import random
import shutil

import pytest
from conftest import FIXTURES, load_script, run_main

PR_QUEUE = load_script("pr-queue-digest", "pr_queue.py")
ITERATION = load_script("iteration-report", "iteration_report.py")
POSTMORTEM = load_script("incident-postmortem-timeline", "postmortem.py")
TRIAGE = load_script("issue-triage-digest", "issue_triage.py")

CASES = {
    "pr_queue": (PR_QUEUE, "pr_queue", lambda d: [str(d)]),
    "iteration": (ITERATION, "iteration", lambda d: [str(d), "--from", "2026-09-14", "--to", "2026-09-25"]),
    "postmortem": (POSTMORTEM, "postmortem",
                   lambda d: [str(d), "--issue", "412", "--check", str(d / "fixture-draft.json")]),
    "issue_triage": (TRIAGE, "issue_triage",
                     lambda d: [str(d), "--keywords", str(d / "fixture-labels-keywords.json")]),
}

ROUNDS = int(os.environ.get("FUZZ_ROUNDS", "60"))
BASE_SEED = int(os.environ.get("FUZZ_SEED", "20261026"))

JUNK_STRINGS = ["", " ", "null", "2026-13-45T99:99:99Z", "yesterday", "-1", "1e309", "NaN", "\x00", "‮", "[bot]",
                "#", "a" * 300, "2026-09-15", "2026-09-15T09:00:00+14:00", "OPEN", "MERGED", "CLOSED"]


def junk(rng: random.Random, depth: int = 0) -> object:
    choice = rng.randrange(9 if depth < 2 else 6)
    if choice == 0:
        return None
    if choice == 1:
        return rng.choice([True, False])
    if choice == 2:
        return rng.choice([0, -1, 1, 2**63, -(2**63), 7])
    if choice == 3:
        return rng.choice([0.5, -3.25, 1e308, float("inf")])
    if choice in (4, 5):
        return rng.choice(JUNK_STRINGS)
    if choice == 6:
        return [junk(rng, depth + 1) for _ in range(rng.randrange(3))]
    if choice == 7:
        return {rng.choice(["login", "number", "createdAt", "name", "state", "x"]): junk(rng, depth + 1)}
    return {}


def paths(node: object, prefix: tuple = ()) -> list[tuple]:
    found = [prefix]
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(paths(value, prefix + (key,)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(paths(value, prefix + (index,)))
    return found


def mutate(rng: random.Random, data: object) -> object:
    if rng.random() < 0.05:
        return junk(rng)
    targets = paths(data)
    for _ in range(rng.randrange(1, 4)):
        path = rng.choice(targets)
        if not path:
            return junk(rng)
        parent = data
        try:
            for step in path[:-1]:
                parent = parent[step]
            last = path[-1]
            action = rng.randrange(4)
            if action == 0 and isinstance(parent, dict):
                parent.pop(last, None)
            elif action == 1 and isinstance(parent[last], list):
                parent[last] = [] if rng.random() < 0.5 else [parent[last]]
            else:
                parent[last] = junk(rng)
        except (KeyError, IndexError, TypeError):
            continue
        targets = paths(data)
    return data


def write_mutation(rng: random.Random, folder) -> None:
    files = sorted(folder.glob("*.json"))
    for path in rng.sample(files, rng.randrange(1, len(files) + 1)):
        text = path.read_text(encoding="utf-8")
        if rng.random() < 0.08:
            path.write_text(text[: rng.randrange(len(text) + 1)], encoding="utf-8")
            continue
        data = mutate(rng, json.loads(text))
        path.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize("case", sorted(CASES))
def test_mutated_exports_never_crash(tmp_path, case):
    script, fixture, argv = CASES[case]
    failures = []
    for round_number in range(ROUNDS):
        seed = BASE_SEED + round_number
        rng = random.Random(f"{case}-{seed}")
        folder = tmp_path / f"r{round_number}"
        shutil.copytree(FIXTURES / fixture, folder)
        write_mutation(rng, folder)
        try:
            rc, _out, err = run_main(script, argv(folder))
        except Exception as exc:  # noqa: BLE001 - the point is to catch anything
            failures.append(f"seed {seed}: {type(exc).__name__}: {exc}")
            continue
        if rc not in (0, 1, 2):
            failures.append(f"seed {seed}: exit {rc}")
        elif rc == 2 and not err.strip():
            failures.append(f"seed {seed}: exit 2 with no message")
    assert not failures, "\n".join(failures[:10])


YAML_PIECES = ["bug:", "bug: [crash, error]", "  - crash", "- orphan", "docs: [typo", "docs: typo]", ": [x]", "# note",
               "\t- tab", "ui: []", "perf: [slow, 'quoted', \"dq\"]", "x: [a, [b]]", "", "   ", "label: - a", "a:b:c",
               "été: [café]", "---", "key: {a: b}"]


def test_random_keyword_maps_never_crash(tmp_path):
    folder = tmp_path / "export"
    shutil.copytree(FIXTURES / "issue_triage", folder)
    failures = []
    for round_number in range(ROUNDS * 2):
        seed = BASE_SEED + round_number
        rng = random.Random(f"keywords-{seed}")
        lines = [rng.choice(YAML_PIECES) for _ in range(rng.randrange(1, 8))]
        kmap = folder / "labels.yaml"
        kmap.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            rc, _out, err = run_main(TRIAGE, [str(folder), "--keywords", str(kmap)])
        except Exception as exc:  # noqa: BLE001
            failures.append(f"seed {seed}: {type(exc).__name__}: {exc} for {lines!r}")
            continue
        if rc not in (0, 1, 2) or (rc == 2 and not err.strip()):
            failures.append(f"seed {seed}: exit {rc} for {lines!r}")
    assert not failures, "\n".join(failures[:10])
