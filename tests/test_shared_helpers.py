"""Tests for _ghexport.py, the helper copied into every skill's scripts/ folder."""
from __future__ import annotations

from datetime import timedelta

from conftest import SKILLS, load_script

COPIES = sorted(SKILLS.glob("*/scripts/_ghexport.py"))
h = load_script("pr-queue-digest", "_ghexport.py")


def test_every_skill_has_an_identical_copy():
    assert len(COPIES) == 4
    texts = {p.read_text(encoding="utf-8") for p in COPIES}
    assert len(texts) == 1, "the _ghexport.py copies differ; copy one over the others"


def test_parse_time_accepts_z_offsets_and_dates():
    assert h.iso(h.parse_time("2026-09-30T12:00:00Z")) == "2026-09-30T12:00:00Z"
    assert h.iso(h.parse_time("2026-09-30T14:00:00+02:00")) == "2026-09-30T12:00:00Z"
    assert h.iso(h.parse_time("2026-09-30")) == "2026-09-30T00:00:00Z"
    assert h.parse_time("") is None and h.parse_time(None) is None and h.parse_time("soon") is None


def test_median_and_nearest_rank_percentile():
    assert h.median([]) is None
    assert h.median([3, 1, 2]) == 2
    assert h.median([1, 2, 3, 10]) == 2.5
    assert h.percentile_nearest_rank([6, 24, 48, 72, 96], 90) == 96
    assert h.percentile_nearest_rank(list(range(1, 11)), 90) == 9
    assert h.percentile_nearest_rank([5], 90) == 5


def test_human_formats():
    assert h.human_hours(0.5) == "30m"
    assert h.human_hours(30) == "30.0h"
    assert h.human_hours(122) == "5.1d (122.0h)"
    assert h.human_delta(timedelta(minutes=43)) == "43m"
    assert h.human_delta(timedelta(hours=2, minutes=50)) == "2h50m"
    assert h.human_delta(timedelta(hours=-16, minutes=-5)) == "-16h05m"


def test_token_is_stable_and_case_insensitive():
    assert h.token("octocat-a") == h.token("OCTOCAT-A")
    assert h.token("octocat-a") != h.token("octocat-b")
    assert h.token("octocat-a").startswith("user-") and len(h.token("octocat-a")) == 11


def test_redactor_replaces_whole_logins_and_mentions_only():
    red = h.Redactor({"octocat-a", "octocat-ab"}, True)
    out = red.text("@octocat-a reviewed; octocat-ab too; not octocat-abc")
    assert "octocat-a " not in out and h.token("octocat-a") in out
    assert h.token("octocat-ab") in out
    assert "octocat-abc" in out
    assert h.Redactor({"octocat-a"}, False).text("octocat-a") == "octocat-a"


def test_redactor_uses_role_names_when_given():
    red = h.Redactor({"octocat-a"}, True, {"octocat-a": "reporter"})
    assert red.text("thanks @octocat-a") == "thanks reporter"
    assert red.name("octocat-a") == "reporter"


def test_file_finders_accept_a_prefix(tmp_path):
    (tmp_path / "fixture-prs.json").write_text("[]", encoding="utf-8")
    (tmp_path / "fixture-timeline-7.json").write_text("[]", encoding="utf-8")
    (tmp_path / "timeline-12.json").write_text("[]", encoding="utf-8")
    assert h.find_file(tmp_path, "prs").name == "fixture-prs.json"
    assert h.find_file(tmp_path, "issues") is None
    assert sorted(h.numbered_files(tmp_path, "timeline")) == [7, 12]


def test_flatten_pages_and_bots():
    assert h.flatten_pages([[1, 2], [3]]) == [1, 2, 3]
    assert h.flatten_pages([{"a": 1}]) == [{"a": 1}]
    assert h.is_bot({"login": "dependabot[bot]"}) and h.is_bot({"login": "x", "is_bot": True})
    assert not h.is_bot({"login": "octocat-a"})
