"""Malformed exports must exit 2 with a message that names the file, never a traceback or exit 1.

Exit 1 means "flagged" for pr_queue.py, issue_triage.py and postmortem.py --check, so a crash that also exits 1 would
look like a finding to a scheduled job. Each case writes a small export into tmp_path; example data only.
"""

from __future__ import annotations

import json

import pytest
from conftest import load_script, run_main

PR_QUEUE = load_script("pr-queue-digest", "pr_queue.py")
ITERATION = load_script("iteration-report", "iteration_report.py")
POSTMORTEM = load_script("incident-postmortem-timeline", "postmortem.py")
TRIAGE = load_script("issue-triage-digest", "issue_triage.py")

GOOD_PR = {"number": 7, "title": "Fix", "url": "https://github.com/example-org/app/pull/7",
           "author": {"login": "octocat-a"}, "createdAt": "2026-09-15T09:00:00Z",
           "state": "OPEN", "isDraft": False, "reviewRequests": [], "reviews": []}
GOOD_ISSUE = {"number": 412, "title": "Outage", "url": "https://github.com/example-org/app/issues/412",
              "author": {"login": "octocat-b"}, "createdAt": "2026-09-15T08:00:00Z", "labels": [], "comments": []}


def folder_with(tmp_path, files: dict[str, object]):
    folder = tmp_path / "export"
    folder.mkdir()
    for name, content in files.items():
        text = content if isinstance(content, str) else json.dumps(content)
        (folder / name).write_text(text, encoding="utf-8")
    return folder


def run(script, folder, *extra):
    argv = {
        PR_QUEUE: [str(folder)],
        ITERATION: [str(folder), "--from", "2026-09-14", "--to", "2026-09-25"],
        POSTMORTEM: [str(folder), "--issue", "412"],
        TRIAGE: [str(folder)],
    }[script]
    return run_main(script, argv + list(extra))


def full_export(**override):
    files = {"prs.json": [GOOD_PR], "issues.json": [GOOD_ISSUE], "issue-412.json": GOOD_ISSUE,
             "timeline-412.json": [], "milestones.json": []}
    files.update(override)
    return files


SCRIPTS = [PR_QUEUE, ITERATION, POSTMORTEM, TRIAGE]
MAIN_FILE = {PR_QUEUE: "prs.json", ITERATION: "prs.json", POSTMORTEM: "issue-412.json", TRIAGE: "issues.json"}


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda m: m.__name__)
def test_good_minimal_export_is_accepted(tmp_path, script):
    rc, out, err = run(script, folder_with(tmp_path, full_export()))
    assert rc in (0, 1), err
    assert out


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda m: m.__name__)
def test_empty_file_says_empty(tmp_path, script):
    name = MAIN_FILE[script]
    rc, out, err = run(script, folder_with(tmp_path, full_export(**{name: ""})))
    assert rc == 2
    assert name in err and "the file is empty" in err
    assert out == ""


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda m: m.__name__)
def test_csv_instead_of_json_is_bad_input(tmp_path, script):
    name = MAIN_FILE[script]
    rc, _, err = run(script, folder_with(tmp_path, full_export(**{name: "number,title\n1,Fix\n"})))
    assert rc == 2
    assert name in err and "not valid JSON" in err


@pytest.mark.parametrize("script", [PR_QUEUE, ITERATION, TRIAGE], ids=lambda m: m.__name__)
def test_object_instead_of_list_names_the_file(tmp_path, script):
    name = MAIN_FILE[script]
    rc, _, err = run(script, folder_with(tmp_path, full_export(**{name: {"items": 3}})))
    assert rc == 2
    assert name in err and "Traceback" not in err


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda m: m.__name__)
def test_number_that_is_not_a_whole_number(tmp_path, script):
    name = MAIN_FILE[script]
    row = dict(GOOD_ISSUE if script in (POSTMORTEM, TRIAGE) else GOOD_PR, number="x")
    rc, _, err = run(script, folder_with(tmp_path, full_export(**{name: row if script is POSTMORTEM else [row]})))
    assert rc == 2
    assert "'x'" in err and "whole number" in err


@pytest.mark.parametrize("script", [PR_QUEUE, ITERATION, TRIAGE], ids=lambda m: m.__name__)
@pytest.mark.parametrize("value", [None, "not-a-date", 12345])
def test_unparseable_created_at_is_bad_input_not_an_empty_report(tmp_path, script, value):
    name = MAIN_FILE[script]
    row = dict(GOOD_ISSUE if script is TRIAGE else GOOD_PR, createdAt=value)
    rc, out, err = run(script, folder_with(tmp_path, full_export(**{name: [row]})))
    assert rc == 2
    assert "createdAt" in err and "re-run the export" in err
    assert out == ""


def test_iteration_report_rejects_a_garbled_merged_at(tmp_path):
    pr = dict(GOOD_PR, mergedAt="yesterday", state="MERGED")
    rc, _, err = run(ITERATION, folder_with(tmp_path, full_export(**{"prs.json": [pr]})))
    assert rc == 2
    assert "PR #7 has mergedAt 'yesterday'" in err


def test_iteration_report_accepts_null_merged_at(tmp_path):
    pr = dict(GOOD_PR, mergedAt=None, closedAt=None)
    rc, _, err = run(ITERATION, folder_with(tmp_path, full_export(**{"prs.json": [pr]})))
    assert rc == 0, err


def test_pr_queue_meta_must_be_an_object(tmp_path):
    rc, _, err = run(PR_QUEUE, folder_with(tmp_path, full_export(**{"meta.json": [1, 2]})))
    assert rc == 2
    assert "meta.json" in err and "JSON object" in err


@pytest.mark.parametrize("script,name", [(PR_QUEUE, "timeline-7.json"), (POSTMORTEM, "timeline-412.json")],
                         ids=["pr_queue", "postmortem"])
def test_timeline_object_names_the_file(tmp_path, script, name):
    rc, _, err = run(script, folder_with(tmp_path, full_export(**{name: {"message": "Not Found"}})))
    assert rc == 2
    assert name in err and "expected a JSON array, found a JSON object" in err


def test_postmortem_rejects_a_garbled_pr_merge_time(tmp_path):
    pr = dict(GOOD_PR, mergedAt="soon")
    rc, _, err = run(POSTMORTEM, folder_with(tmp_path, full_export(**{"pr-7.json": pr})))
    assert rc == 2
    assert "pr-7.json" in err and "mergedAt 'soon'" in err


def test_numeric_string_numbers_still_work(tmp_path):
    rc, _, err = run(PR_QUEUE, folder_with(tmp_path, full_export(**{"prs.json": [dict(GOOD_PR, number="7")]})))
    assert rc in (0, 1), err


def test_bool_is_not_a_number(tmp_path):
    rc, _, err = run(TRIAGE, folder_with(tmp_path, full_export(**{"issues.json": [dict(GOOD_ISSUE, number=True)]})))
    assert rc == 2
    assert "whole number" in err
