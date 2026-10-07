"""Tests for postmortem.py over tests/fixtures/postmortem (incident issue #412).

Planted: the mitigation PR #415 merged at 09:02, 43 minutes before the "mitigated" label (09:45). Also: an
assignment two minutes before the first responder comment, a "resolved" label six minutes before the close, a PR
merged the day before (#409), and an open follow-up PR (#418).
"""
from __future__ import annotations

import json
import re

from conftest import FIXTURES, load_script, read_fixture, run_json, run_main, write_fixture

FOLDER = str(FIXTURES / "postmortem")
mod = load_script("incident-postmortem-timeline", "postmortem.py")


def report(*extra: str, folder: str = FOLDER) -> dict:
    rc, rep = run_json(mod, [folder, "--issue", "412", "--json", *extra])
    assert rc == 0
    return rep


def test_check_draft_reports_only_the_unmatched_table_time(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(read_fixture(FIXTURES / "postmortem", "fixture-draft.json")["draft"])
    rc, rep = run_json(mod, [FOLDER, "--issue", "412", "--check", str(draft), "--json"])
    assert rc == 1
    assert [(item["line"], item["time"]) for item in rep["draft_problems"]] == [(7, "23:59")]
    rc, out, err = run_main(mod, [FOLDER, "--issue", "412", "--check", str(draft)])
    assert rc == 1
    assert "draft line 7: 23:59:" in err
    assert "draft line" not in out


def test_check_draft_accepts_one_minute_tolerance_and_ignores_prose(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(
        "Prose at 23:59 is not a table event.\n| 08:06 | Close to detection |\n"
        "| 2026-09-20T11:05:00+00:00 | Closed |\n"
    )
    rows = report()["timeline"]
    close = next(r["time"] for r in rows if "Closed" in r["what"] or "closed" in r["what"])
    draft.write_text(draft.read_text().replace("2026-09-20T11:05:00+00:00", close))
    rc, rep = run_json(mod, [FOLDER, "--issue", "412", "--check", str(draft), "--json"])
    assert rc == 0 and rep["draft_problems"] == []


def test_check_draft_matches_timezone_offsets_and_skips_code_tables():
    rows = [{"time": "2026-09-20T09:02:00Z"}]
    assert mod.check_draft(
        "| 2026-09-20T11:02:30+02:00 | same instant |\n"
        "```\n| 23:59 | code, not an event |\n```\n", rows
    ) == []
    assert mod.check_draft("| 2026-09-21T09:02:00Z | wrong day |", rows)[0]["line"] == 1


def test_check_missing_draft_is_bad_input(tmp_path):
    rc, _, err = run_main(mod, [FOLDER, "--issue", "412", "--check", str(tmp_path / "absent.md")])
    assert rc == 2 and "cannot read" in err


def phase(rep: dict, name: str) -> dict:
    return next(p for p in rep["phases"] if p["phase"] == name)


def test_planted_mitigation_pr_before_label_uses_the_pr_merge():
    p = phase(report(), "mitigated")
    assert p["time"] == "2026-09-20T09:02:00Z"
    assert p["cite"].startswith("PR #415 mergedAt")
    assert [s["cite"] for s in p["signals"]] == ["PR #415 mergedAt, merge commit 415b000", "event 9010"]


def test_planted_gap_is_reported_as_a_note_and_a_question():
    rep = report()
    note = next(n for n in rep["phase_notes"] if n["phase"] == "mitigated")
    assert note["gap"] == "43m"
    assert note["later"] == "event 9010"
    assert any("43m before event 9010" in q and q.endswith("?") for q in rep["questions"])


def test_detected_is_the_issue_creation():
    p = phase(report(), "detected")
    assert p["time"] == "2026-09-20T08:05:00Z"
    assert p["cite"] == "issue #412 createdAt"


def test_acknowledged_is_the_earliest_of_assignment_and_comment():
    p = phase(report(), "acknowledged")
    assert p["time"] == "2026-09-20T08:10:00Z"
    assert p["cite"] == "event 9003"
    assert p["since_detection"] == "5m"
    assert [s["cite"] for s in p["signals"]][:2] == ["event 9003", "comment 5001"]


def test_resolved_is_the_label_before_the_close():
    p = phase(report(), "resolved")
    assert p["time"] == "2026-09-20T10:55:00Z"
    assert p["cite"] == "event 9012"
    assert p["since_detection"] == "2h50m"


def test_every_timeline_row_has_a_citation_and_rows_are_in_time_order():
    rows = report()["timeline"]
    assert len(rows) == 16
    assert all(r["cite"] for r in rows)
    assert [r["time"] for r in rows] == sorted(r["time"] for r in rows)


def test_citations_point_at_event_ids_comment_ids_or_prs():
    pattern = re.compile(r"^(event \d+|comment \d+|issue #412 createdAt|PR #\d+ (mergedAt|createdAt).*|"
                         r"timeline row \d+ \(cross-referenced, no event id\))$")
    for r in report()["timeline"]:
        assert pattern.match(r["cite"]), r["cite"]


def test_comments_are_not_duplicated_between_issue_and_timeline():
    cites = [r["cite"] for r in report()["timeline"] if r["cite"].startswith("comment")]
    assert cites == ["comment 5001", "comment 5002", "comment 5003", "comment 5004"]


def test_comments_from_the_issue_export_are_used_when_the_timeline_has_none(fixture_copy):
    folder = fixture_copy("postmortem")
    events = [e for e in read_fixture(folder, "fixture-timeline-412.json") if e.get("event") != "commented"]
    write_fixture(folder, "fixture-timeline-412.json", events)
    rows = report(folder=str(folder))["timeline"]
    assert [r["cite"] for r in rows if r["cite"].startswith("comment")] == [
        "comment 5001", "comment 5002", "comment 5003", "comment 5004"]


def test_change_merged_before_detection_is_listed_by_time_only():
    rep = report()
    row = next(r for r in rep["timeline"] if r["cite"].startswith("PR #409"))
    assert row["since_detection"] == "-16h05m"
    q = next(q for q in rep["questions"] if "PR #409" in q)
    assert "Was it related?" in q and "listed by time only" in q


def test_lookback_hides_older_changes():
    rep = report("--lookback-hours", "12")
    assert not any(r["cite"].startswith("PR #409") for r in rep["timeline"])


def test_open_follow_up_pr_becomes_a_question():
    rep = report()
    assert any(q.startswith("PR #418 is still open") for q in rep["questions"])


def test_questions_are_questions_not_conclusions():
    for q in report()["questions"]:
        assert q.rstrip().endswith("?"), q
        assert "root cause" not in q.lower()
        assert "caused" not in q.lower()


def test_people_are_roles_in_order_of_first_appearance():
    people = report()["people"]
    assert [p["role"] for p in people] == ["reporter", "responder-1", "responder-2", "change-author-1"]
    assert people[0]["login"] == "octocat-oncall"


def test_redact_shows_roles_only_everywhere():
    rc, out, _ = run_main(mod, [FOLDER, "--issue", "412", "--json", "--redact"])
    assert rc == 0
    assert "octocat" not in out
    rep = json.loads(out)
    assert all(p["login"] is None for p in rep["people"])
    assert any("Assigned to responder-1" == r["what"] for r in rep["timeline"])
    assert any("reporter can you confirm" in r["what"] for r in rep["timeline"])


def test_redacted_markdown_has_no_logins():
    rc, out, _ = run_main(mod, [FOLDER, "--issue", "412", "--redact"])
    assert rc == 0 and "octocat" not in out
    assert "(names withheld)" in out


def test_missing_phase_is_not_found_never_estimated(fixture_copy):
    folder = fixture_copy("postmortem")
    events = [e for e in read_fixture(folder, "fixture-timeline-412.json")
              if not (e.get("event") == "labeled" and e["label"]["name"] in ("mitigated",))]
    write_fixture(folder, "fixture-timeline-412.json", events)
    prs = [p for p in read_fixture(folder, "fixture-prs.json") if p["number"] != 415]
    write_fixture(folder, "fixture-prs.json", prs)
    rep = report(folder=str(folder))
    p = phase(rep, "mitigated")
    assert p["time"] is None and p["signal"] == "not found in the export"
    assert any("No 'mitigated' signal" in q for q in rep["questions"])
    assert rep["referenced_prs_missing_from_export"] == [415]


def test_custom_label_patterns(fixture_copy):
    folder = fixture_copy("postmortem")
    events = read_fixture(folder, "fixture-timeline-412.json")
    for e in events:
        if e.get("event") == "labeled" and e["label"]["name"] == "mitigated":
            e["label"]["name"] = "state/stable"
    write_fixture(folder, "fixture-timeline-412.json", events)
    rep = report("--mitigated-labels", "^state/stable$", "--mitigation-pattern", "^$", folder=str(folder))
    assert phase(rep, "mitigated")["cite"] == "event 9010"


def test_markdown_skeleton_sections_and_citations():
    rc, out, _ = run_main(mod, [FOLDER, "--issue", "412"])
    assert rc == 0
    for heading in ("# Postmortem: Checkout API returning 502 errors (#412)", "## Summary", "## Impact", "## Phases",
                    "## Timeline", "## People involved", "## Questions for the review", "## Action items"):
        assert heading in out
    assert "Blameless" in out
    assert "[comment 5001](https://github.com/example-org/shop/issues/412#issuecomment-5001)" in out
    assert "| mitigated | 2026-09-20T09:02:00Z | 57m |" in out


def test_wrong_issue_number_and_missing_files_exit_2(tmp_path):
    rc, _, err = run_main(mod, [FOLDER, "--issue", "999"])
    assert rc == 2
    rc, _, err = run_main(mod, [str(tmp_path), "--issue", "412"])
    assert rc == 2 and "issue-412.json" in err


def test_issue_json_without_number_suffix_is_accepted(fixture_copy):
    folder = fixture_copy("postmortem")
    (folder / "fixture-issue-412.json").rename(folder / "issue.json")
    (folder / "fixture-timeline-412.json").rename(folder / "timeline.json")
    assert len(report(folder=str(folder))["timeline"]) == 16


def test_bad_pattern_exits_2():
    rc, _, err = run_main(mod, [FOLDER, "--issue", "412", "--ack-labels", "("])
    assert rc == 2 and "bad pattern" in err


def test_help():
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "usage: postmortem.py" in out


def test_one_file_per_pr_is_read(fixture_copy):
    folder = fixture_copy("postmortem")
    for pr in read_fixture(folder, "fixture-prs.json"):
        write_fixture(folder, f"pr-{pr['number']}.json", pr)
    (folder / "fixture-prs.json").unlink()
    rep = report(folder=str(folder))
    assert phase(rep, "mitigated")["cite"].startswith("PR #415 mergedAt")
    assert "pr-415.json" in rep["source_files"]
