"""Tests for iteration_report.py over tests/fixtures/iteration (window 2026-09-14 to 2026-09-25, Sprint 38).

Planted: two carried-over issues (#204, #205) and one PR merged just after the window (#306 at 2026-09-26T03:00Z),
plus a PR merged before it (#309), one closed unmerged (#308), one linked through the PR body only (#304), one
bot PR merged without review (#307), and one issue closed as not planned (#208).
Cycle times (first commit to merge): 6, 24, 48, 72, 96 hours. Review turnaround: 4, 6, 22, 24 hours.
"""
from __future__ import annotations

from conftest import FIXTURES, load_script, read_fixture, run_json, run_main, write_fixture

FOLDER = str(FIXTURES / "iteration")
WINDOW = ["--from", "2026-09-14", "--to", "2026-09-25"]
mod = load_script("iteration-report", "iteration_report.py")


def report(*extra: str, folder: str = FOLDER) -> dict:
    rc, rep = run_json(mod, [folder, *WINDOW, "--json", *extra])
    assert rc == 0
    return rep


def numbers(rows: list) -> list[int]:
    return [r["number"] for r in rows]


def test_planted_carried_over_issues():
    assert numbers(report()["carried_over"]) == [204, 205]


def test_pr_merged_outside_the_window_is_not_shipped():
    rep = report()
    assert 306 not in numbers(rep["shipped"])
    outside = {r["number"]: r for r in rep["merged_outside_window"]}
    assert outside[306]["when"] == "after"
    assert outside[306]["merged"] == "2026-09-26T03:00:00Z"
    assert outside[309]["when"] == "before"


def test_shipped_prs_and_their_issues():
    rep = report()
    assert numbers(rep["shipped"]) == [301, 302, 303, 304, 307]
    assert numbers(rep["shipped_issues"]) == [201, 202, 203, 207]
    assert rep["shipped_without_issue"] == [307]


def test_issue_link_falls_back_to_body_keywords():
    pr = next(p for p in report()["shipped"] if p["number"] == 304)
    assert pr["issues"] == [207]
    assert pr["issues_basis"] == "PR body keywords"


def test_body_keywords_need_a_closing_verb():
    assert mod.linked_issues({"body": "Part of #205"}) == ([], "none")
    assert mod.linked_issues({"body": "Fixes: #9 and resolves #10"})[0] == [9, 10]


def test_scope_is_the_one_milestone_due_in_the_window():
    scope = report()["scope"]
    assert scope["milestone"] == "Sprint 38"
    assert scope["issues"] == [201, 202, 203, 204, 205, 207, 208]
    assert "due in the window" in scope["basis"]


def test_completed_and_not_planned_are_separate():
    rep = report()
    assert numbers(rep["completed"]) == [201, 202, 203, 207]
    assert numbers(rep["not_planned"]) == [208]


def test_newly_opened_marks_scope():
    rows = report()["newly_opened"]
    assert numbers(rows) == [207, 209, 210]
    assert [r["in_scope"] for r in rows] == [True, False, False]


def test_closed_unmerged_is_not_shipped():
    rep = report()
    assert numbers(rep["closed_unmerged"]) == [308]


def test_cycle_time_median_and_p90_from_first_commit():
    ct = report()["metrics"]["cycle_time"]
    assert ct["n"] == 5
    assert ct["median"] == 48.0
    assert ct["p90"] == 96.0
    assert ct["start_bases"] == ["first commit"]
    assert ct["rows"] == [301, 302, 303, 304, 307]


def test_cycle_time_from_pr_open():
    ct = report("--cycle-start", "pr-open")["metrics"]["cycle_time"]
    # 45h, 72h, 23h, 54.0h, 5.9h from PR creation
    assert ct["median"] == 45.0
    assert ct["p90"] == 72.0
    assert ct["start_bases"] == ["PR opened"]


def test_missing_commits_fall_back_to_pr_open_and_say_so(fixture_copy):
    folder = fixture_copy("iteration")
    prs = read_fixture(folder, "fixture-prs.json")
    for p in prs:
        if p["number"] == 302:
            p["commits"] = []
    write_fixture(folder, "fixture-prs.json", prs)
    rep = report(folder=str(folder))
    pr = next(p for p in rep["shipped"] if p["number"] == 302)
    assert pr["cycle_start_basis"] == "PR opened (no commits in the export)"
    assert pr["cycle_hours"] == 72.0
    assert "PR opened (no commits in the export)" in rep["metrics"]["cycle_time"]["start_bases"]


def test_review_turnaround_excludes_self_reviews_and_lists_unreviewed():
    rt = report()["metrics"]["review_turnaround"]
    assert rt["n"] == 4
    assert rt["median"] == 14.0
    assert rt["merged_without_review"] == [307]
    pr301 = next(p for p in report()["shipped"] if p["number"] == 301)
    assert pr301["review_hours"] == 22.0  # the author's own comment at +1h is ignored


def test_explicit_milestone_overrides(fixture_copy):
    rep = report("--milestone", "Sprint 39")
    assert rep["scope"]["issues"] == [211]
    assert rep["carried_over"] == []  # #211 was created after the window


def test_unknown_milestone_exits_2():
    rc, _, err = run_main(mod, [FOLDER, *WINDOW, "--milestone", "Sprint 99"])
    assert rc == 2 and "Sprint 99" in err


def test_without_milestones_scope_is_assigned_open_issues(fixture_copy):
    folder = fixture_copy("iteration")
    (folder / "fixture-milestones.json").unlink()
    issues = read_fixture(folder, "fixture-issues.json")
    for i in issues:
        i["milestone"] = None
    write_fixture(folder, "fixture-issues.json", issues)
    rep = report(folder=str(folder))
    assert rep["scope"]["milestone"] is None
    assert "open and assigned at the window start" in rep["scope"]["basis"]
    assert rep["scope"]["issues"] == [201, 202, 203, 204, 205, 208]
    assert numbers(rep["carried_over"]) == [204, 205]


def test_team_level_only_no_people_in_output():
    rc, out, _ = run_main(mod, [FOLDER, *WINDOW, "--json"])
    assert "octocat" not in out
    assert "dependabot" not in out
    assert '"author"' not in out


def test_markdown_summary_cites_rows_for_every_number():
    rc, out, _ = run_main(mod, [FOLDER, *WINDOW])
    assert rc == 0
    assert "Shipped 5 PRs (#301, #302, #303, #304, #307)" in out
    assert "carried over 2 (#204, #205)" in out
    assert "median 2.0d (48.0h), p90 4.0d (96.0h)" in out
    assert "median 14.0h" in out
    assert "2 PRs merged outside the window (#306, #309)" in out
    assert "Team level only" in out


def test_window_end_is_inclusive_of_the_whole_day():
    rep = report()
    assert rep["window"]["to_exclusive"] == "2026-09-26T00:00:00Z"
    rc, rep2 = run_json(mod, [FOLDER, "--from", "2026-09-14", "--to", "2026-09-26", "--json"])
    assert 306 in numbers(rep2["shipped"])


def test_redact_option_runs():
    rc, out, _ = run_main(mod, [FOLDER, *WINDOW, "--redact"])
    assert rc == 0 and "octocat" not in out


def test_bad_window_exits_2():
    rc, _, err = run_main(mod, [FOLDER, "--from", "2026-09-25", "--to", "2026-09-14"])
    assert rc == 2 and "before" in err
    rc, _, err = run_main(mod, [FOLDER, "--from", "last week", "--to", "2026-09-14"])
    assert rc == 2


def test_missing_files_exit_2(tmp_path):
    rc, _, err = run_main(mod, [str(tmp_path), *WINDOW])
    assert rc == 2 and "issues.json" in err


def test_help():
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "usage: iteration_report.py" in out


def test_split_exports_are_merged_by_number(fixture_copy):
    folder = fixture_copy("iteration")
    prs = read_fixture(folder, "fixture-prs.json")
    issues = read_fixture(folder, "fixture-issues.json")
    (folder / "fixture-prs.json").unlink()
    (folder / "fixture-issues.json").unlink()
    write_fixture(folder, "prs-open.json", [p for p in prs if p["state"] == "OPEN"])
    write_fixture(folder, "prs-closed.json", [p for p in prs if p["state"] != "OPEN"])
    write_fixture(folder, "issues-open.json", [i for i in issues if i["state"] == "OPEN"])
    write_fixture(folder, "issues-closed.json", issues)  # overlaps nothing open; duplicates collapse by number
    rep = report(folder=str(folder))
    assert numbers(rep["shipped"]) == [301, 302, 303, 304, 307]
    assert numbers(rep["carried_over"]) == [204, 205]
    assert rep["source_files"] == ["fixture-milestones.json", "issues-closed.json", "issues-open.json",
                                   "prs-closed.json", "prs-open.json"]
