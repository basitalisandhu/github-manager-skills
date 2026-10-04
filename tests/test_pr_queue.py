"""Tests for pr_queue.py over tests/fixtures/pr_queue, a saved gh pr list export with planted cases.

As of 2026-09-30T12:00:00Z (fixture-meta.json). Planted: #101 waits 5 days on one reviewer (octocat-r) who has 9
other pending requests; #102 failing checks; #103 merge conflicts; #111 changes requested with no commit since;
#112 commits after a changes request with no re-request; #113 stale draft; #115 approved but not merged; #116 no
reviewer; #118 waiting 30 hours on two reviewers. #104 to #110, #114, #117 and #119 must not be flagged.
"""
from __future__ import annotations

from conftest import FIXTURES, load_script, read_fixture, run_json, run_main, write_fixture

FOLDER = str(FIXTURES / "pr_queue")
mod = load_script("pr-queue-digest", "pr_queue.py")
helpers = load_script("pr-queue-digest", "_ghexport.py")


def report(*extra: str) -> dict:
    rc, rep = run_json(mod, [FOLDER, "--json", *extra])
    assert rc in (0, 1)
    return rep


def flagged(rep: dict, check: str) -> list[int]:
    return rep["summary"]["by_check"][check]


def test_planted_reviewer_bottleneck_is_blocked_on_reviewer():
    rep = report()
    assert flagged(rep, "blocked-on-reviewer") == [101]
    row = next(f for f in rep["findings"] if f["check"] == "blocked-on-reviewer")
    assert row["reviewer"] == "octocat-r"
    assert row["reviewer_other_requests"] == list(range(102, 111))
    assert len(row["reviewer_other_requests"]) == 9
    assert row["url"] == "https://github.com/example-org/shop/pull/101"


def test_wait_is_measured_from_the_review_request_event_when_a_timeline_exists():
    row = next(f for f in report()["findings"] if f["check"] == "waiting-on-review" and f["pr"] == 101)
    assert row["since"] == "2026-09-25T10:00:00Z"
    assert row["hours"] == 122.0
    assert row["basis"] == "review requested (timeline)"


def test_latest_review_request_wins_over_an_earlier_one():
    row = next(f for f in report()["findings"] if f["check"] == "waiting-on-review" and f["pr"] == 118)
    assert row["since"] == "2026-09-29T06:00:00Z"
    assert row["hours"] == 30.0


def test_waiting_on_review_lists_only_prs_over_the_threshold():
    assert flagged(report(), "waiting-on-review") == [101, 118]


def test_raising_the_threshold_drops_the_shorter_wait():
    rep = report("--hours", "48")
    assert flagged(rep, "waiting-on-review") == [101]
    assert rep["thresholds"]["hours"] == 48.0


def test_without_a_timeline_the_wait_falls_back_to_pr_creation(fixture_copy):
    folder = fixture_copy("pr_queue")
    (folder / "fixture-timeline-101.json").unlink()
    rc, rep = run_json(mod, [str(folder), "--json"])
    row = next(f for f in rep["findings"] if f["check"] == "waiting-on-review" and f["pr"] == 101)
    assert row["since"] == "2026-09-25T09:00:00Z"
    assert row["basis"] == "PR opened (no timeline export)"


def test_reviewer_load_threshold_controls_blocking():
    assert flagged(report("--reviewer-load", "10"), "blocked-on-reviewer") == []
    assert flagged(report("--reviewer-load", "9"), "blocked-on-reviewer") == [101]


def test_failing_checks_name_the_check():
    rep = report()
    assert flagged(rep, "failing-checks") == [102]
    row = next(f for f in rep["findings"] if f["check"] == "failing-checks")
    assert row["checks"] == ["test (failure)"]


def test_conflicts_need_a_rebase():
    assert flagged(report(), "needs-rebase") == [103]


def test_changes_requested_without_new_commits():
    rep = report()
    assert flagged(rep, "changes-requested-no-new-commits") == [111]
    row = next(f for f in rep["findings"] if f["check"] == "changes-requested-no-new-commits")
    assert row["since"] == "2026-09-22T15:00:00Z"
    assert row["hours"] == 189.0


def test_commits_after_changes_request_without_re_request():
    rep = report()
    assert flagged(rep, "re-request-needed") == [112]
    assert flagged(rep, "changes-requested-no-new-commits") == [111]


def test_stale_draft_and_fresh_draft():
    rep = report()
    assert flagged(rep, "stale-draft") == [113]
    assert 114 not in rep["summary"]["flagged_prs"]


def test_stale_days_option():
    assert flagged(report("--stale-days", "60"), "stale-draft") == []


def test_approved_not_merged_and_recent_approval_ignored():
    rep = report()
    assert flagged(rep, "approved-not-merged") == [115]
    assert 119 not in rep["summary"]["flagged_prs"]


def test_no_reviewer_requested():
    assert flagged(report(), "no-reviewer") == [116]


def test_true_negatives_are_not_flagged():
    rep = report()
    for number in [*range(104, 111), 114, 117, 119]:
        assert number not in rep["summary"]["flagged_prs"], number


def test_flagged_set_is_exact():
    assert report()["summary"]["flagged_prs"] == [101, 102, 103, 111, 112, 113, 115, 116, 118]


def test_review_queue_counts_sorted_by_name_not_by_load():
    queue = report()["review_queue"]
    assert [r["reviewer"] for r in queue] == ["octocat-b", "octocat-e", "octocat-r", "team platform"]
    by = {r["reviewer"]: r for r in queue}
    assert by["octocat-r"]["pending"] == 10
    assert by["octocat-r"]["prs"] == list(range(101, 111))
    assert by["octocat-r"]["over_threshold"] == 1
    assert by["octocat-r"]["oldest_hours"] == 122.0
    assert by["team platform"]["pending"] == 2
    assert by["octocat-b"]["prs"] == [103, 118]


def test_review_queue_holds_counts_only():
    for row in report()["review_queue"]:
        assert set(row) == {"reviewer", "kind", "pending", "over_threshold", "oldest_hours", "prs"}


def test_one_next_action_per_flagged_pr_each_citing_the_pr():
    rep = report()
    actions = {a["pr"]: a for a in rep["next_actions"]}
    assert sorted(actions) == rep["summary"]["flagged_prs"]
    assert actions[101]["action"] == "re-request"
    assert actions[102]["action"] == "fix checks"
    assert actions[103]["action"] == "rebase"
    assert actions[111]["action"] == "nudge"
    assert actions[112]["action"] == "re-request"
    assert actions[113]["action"] == "close as stale"
    assert actions[115]["action"] == "merge"
    assert actions[116]["action"] == "request a reviewer"
    assert actions[118]["action"] == "nudge"
    for a in rep["next_actions"]:
        assert a["url"].endswith(f"/pull/{a['pr']}")


def test_every_finding_cites_a_pr_url():
    for f in report()["findings"]:
        assert f["url"] == f"https://github.com/example-org/shop/pull/{f['pr']}"


def test_summary_counts_and_bots():
    s = report()["summary"]
    assert s["open_prs"] == 19
    assert s["drafts"] == 2
    assert s["bot_authored"] == [117]


def test_as_of_comes_from_meta_and_now_overrides():
    assert report()["as_of"] == "2026-09-30T12:00:00Z"
    rep = report("--now", "2026-09-25T12:00:00Z")
    assert rep["as_of_source"] == "--now"
    assert 101 not in flagged(rep, "waiting-on-review")


def test_redact_tokenises_every_login():
    rc, out, _ = run_main(mod, [FOLDER, "--json", "--redact"])
    assert "octocat" not in out
    assert helpers.token("octocat-r") in out
    assert helpers.token("octocat-r") == helpers.token("Octocat-R")


def test_redact_also_covers_text_and_markdown():
    for flag in ([], ["--markdown"]):
        rc, out, _ = run_main(mod, [FOLDER, "--redact", *flag])
        assert rc == 1
        assert "octocat" not in out


def test_markdown_digest_links_every_pr():
    rc, out, _ = run_main(mod, [FOLDER, "--markdown"])
    assert rc == 1
    assert "## PR queue digest: example-org/shop" in out
    assert "| re-request | [#101](https://github.com/example-org/shop/pull/101) |" in out
    assert "Counts only" in out


def test_text_output_lists_checks_and_actions():
    rc, out, _ = run_main(mod, [FOLDER])
    assert rc == 1
    assert "blocked-on-reviewer (1)" in out
    assert "Next actions" in out


def test_exit_zero_when_nothing_is_flagged(fixture_copy):
    folder = fixture_copy("pr_queue")
    prs = [p for p in read_fixture(folder, "fixture-prs.json") if p["number"] in (104, 117, 119)]
    write_fixture(folder, "fixture-prs.json", prs)
    rc, rep = run_json(mod, [str(folder), "--json"])
    assert rc == 0
    assert rep["findings"] == [] and rep["next_actions"] == []


def test_slurped_pages_are_accepted(fixture_copy):
    folder = fixture_copy("pr_queue")
    prs = read_fixture(folder, "fixture-prs.json")
    write_fixture(folder, "fixture-prs.json", [prs[:10], prs[10:]])
    rc, rep = run_json(mod, [str(folder), "--json"])
    assert rep["summary"]["open_prs"] == 19


def test_bad_input_exits_2(tmp_path):
    rc, _, err = run_main(mod, [str(tmp_path)])
    assert rc == 2 and "no prs.json" in err
    (tmp_path / "prs.json").write_text("{not json", encoding="utf-8")
    rc, _, err = run_main(mod, [str(tmp_path)])
    assert rc == 2 and "not valid JSON" in err
    rc, _, _ = run_main(mod, [str(tmp_path / "missing")])
    assert rc == 2


def test_bad_now_exits_2():
    rc, _, err = run_main(mod, [FOLDER, "--now", "yesterday"])
    assert rc == 2 and "--now" in err


def test_help():
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "usage: pr_queue.py" in out
