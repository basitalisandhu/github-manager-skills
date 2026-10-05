"""Tests for issue_triage.py over synthetic gh issue list exports built inside each test.

As of 2026-10-05T00:00:00Z. Example handles only (octocat-*). Planted: #1 unlabelled, unanswered and popular;
#2 answered by a maintainer, labelled, fresh (never flagged); #3 stale; #4 a reworded copy of #1's title.
"""

from __future__ import annotations

import json

from conftest import load_script, run_json, run_main

mod = load_script("issue-triage-digest", "issue_triage.py")
NOW = "2026-10-05T00:00:00Z"


def issue(number, title, created, updated=None, labels=(), comments=(), thumbs=0, author="octocat-a", **extra):
    row = {
        "number": number,
        "title": title,
        "url": f"https://github.com/example-org/app/issues/{number}",
        "author": {"login": author},
        "labels": [{"name": n} for n in labels],
        "assignees": [],
        "createdAt": created,
        "updatedAt": updated or created,
        "comments": [{"author": {"login": who}, "createdAt": created} for who in comments],
        "reactionGroups": [{"content": "THUMBS_UP", "users": {"totalCount": thumbs}}] if thumbs else [],
    }
    row.update(extra)
    return row


def export(tmp_path, rows, meta=True, name="issues.json"):
    folder = tmp_path / "export"
    folder.mkdir(exist_ok=True)
    (folder / name).write_text(json.dumps(rows), encoding="utf-8")
    if meta:
        (folder / "meta.json").write_text(json.dumps({"repo": "example-org/app", "exported_at": NOW}), encoding="utf-8")
    return folder


BACKLOG = [
    issue(1, "App crashes when saving large file", "2026-09-01T00:00:00Z", comments=["octocat-a"], thumbs=7),
    issue(2, "Add dark mode setting", "2026-10-01T00:00:00Z", labels=["enhancement"], comments=["octocat-m"]),
    issue(3, "Docs typo in install guide", "2026-06-01T00:00:00Z", labels=["documentation"], comments=["octocat-m"]),
    issue(4, "Crashes when saving a large file", "2026-09-20T00:00:00Z", labels=["bug"], comments=["octocat-m"]),
]


def test_checks_fire_on_planted_issues_and_cite_them(tmp_path):
    rc, rep = run_json(mod, [str(export(tmp_path, BACKLOG)), "--json"])
    assert rc == 1
    by = rep["summary"]["by_check"]
    assert by == {
        "unlabelled": [1],
        "unanswered": [1],
        "possible-duplicate": [4],
        "stale": [3],
        "popular": [1],
    }
    four = next(r for r in rep["issues"] if r["number"] == 4)
    assert four["duplicate_of"] == 1 and four["similarity"] >= 0.6
    assert four["url"] == "https://github.com/example-org/app/issues/4"
    assert rep["as_of"] == NOW and rep["as_of_source"] == "meta.json exported_at"
    assert 2 not in rep["summary"]["flagged"]


def test_bot_comments_do_not_count_as_an_answer_and_thresholds_apply(tmp_path):
    rows = [issue(5, "Login fails", "2026-09-30T00:00:00Z", labels=["bug"], comments=["helper-bot[bot]"])]
    folder = export(tmp_path, rows)
    rc, rep = run_json(mod, [str(folder), "--json"])
    assert rc == 0 and rep["summary"]["flagged"] == []
    rc, rep = run_json(mod, [str(folder), "--json", "--unanswered-days", "3"])
    assert rc == 1 and rep["summary"]["by_check"]["unanswered"] == [5]


def test_keyword_map_yaml_suggests_missing_labels_only(tmp_path):
    folder = export(tmp_path, BACKLOG)
    kw = tmp_path / "labels.yml"
    kw.write_text(
        '# label map\nbug: [crash, crashes, error]\ndocumentation:\n  - docs\n  - typo\n"good first issue": [typo]\n',
        encoding="utf-8",
    )
    rc, rep = run_json(mod, [str(folder), "--json", "--keywords", str(kw)])
    suggested = {r["number"]: r["suggested_labels"] for r in rep["issues"]}
    assert suggested[1] == ["bug"]
    assert suggested[3] == ["good first issue"]
    assert suggested[4] == []
    assert rep["summary"]["suggested_labels"] == {"bug": [1], "good first issue": [3]}


def test_keyword_map_json_and_body_matching(tmp_path):
    rows = [issue(6, "Something odd", "2026-10-04T00:00:00Z", labels=["triage"], body="Got a Traceback here")]
    folder = export(tmp_path, rows)
    kw = tmp_path / "labels.json"
    kw.write_text(json.dumps({"bug": ["traceback"]}), encoding="utf-8")
    rc, rep = run_json(mod, [str(folder), "--json", "--keywords", str(kw)])
    assert rc == 0 and rep["issues"][0]["suggested_labels"] == ["bug"]


def test_markdown_out_folder_and_redaction(tmp_path):
    rows = [issue(7, "Crash reported by octocat-b", "2026-09-01T00:00:00Z", author="octocat-b")]
    folder = export(tmp_path, rows)
    out = tmp_path / "triage"
    rc, stdout, _ = run_main(mod, [str(folder), "--out", str(out), "--redact"])
    assert rc == 1 and "issue-triage.md" in stdout
    md = (out / "issue-triage.md").read_text(encoding="utf-8")
    data = json.loads((out / "issue-triage.json").read_text(encoding="utf-8"))
    assert "[#7](https://github.com/example-org/app/issues/7)" in md and "octocat-b" not in md
    assert data["summary"]["by_check"]["unlabelled"] == [7]
    assert "octocat" not in json.dumps(data)


def test_closed_issues_ignored_split_exports_merged_and_no_meta(tmp_path):
    folder = export(
        tmp_path, [issue(8, "Old", "2026-01-01T00:00:00Z", state="CLOSED")], meta=False, name="issues-a.json"
    )
    export(tmp_path, [issue(9, "New thing", "2026-10-04T00:00:00Z", labels=["x"])], meta=False, name="issues-b.json")
    rc, rep = run_json(mod, [str(folder), "--json", "--now", NOW])
    assert rep["summary"]["open_issues"] == 1 and rep["as_of_source"] == "--now" and rc == 0
    rc, rep = run_json(mod, [str(folder), "--json"])
    assert rep["as_of_source"].startswith("current time")


def test_bad_input_exits_2(tmp_path):
    assert run_main(mod, [str(tmp_path / "missing")])[0] == 2
    empty = tmp_path / "empty"
    empty.mkdir()
    rc, _, err = run_main(mod, [str(empty)])
    assert rc == 2 and "no issues.json" in err
    folder = export(tmp_path, BACKLOG)
    bad = tmp_path / "bad.yml"
    bad.write_text("bug: crash\n", encoding="utf-8")
    assert run_main(mod, [str(folder), "--keywords", str(bad)])[0] == 2
    assert run_main(mod, [str(folder), "--now", "soon"])[0] == 2
    assert run_main(mod, [str(folder), "--similarity", "0"])[0] == 2
    (folder / "issues.json").write_text("{not json", encoding="utf-8")
    assert run_main(mod, [str(folder)])[0] == 2


def test_text_output_is_deterministic(tmp_path):
    folder = export(tmp_path, BACKLOG)
    first = run_main(mod, [str(folder)])
    second = run_main(mod, [str(folder)])
    assert first == second and first[0] == 1
    assert "possible-duplicate: 1 (#4)" in first[1]
