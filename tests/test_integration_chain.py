"""End-to-end chain over one export folder: an incident inside a sprint.

A manager exports one repository once and runs all four skills on the same folder through the github-manager
dispatcher (scripts/cli.py), the way the container image and the Python package run them:

1. postmortem builds the timeline of incident #412 and names the mitigating PR;
2. iteration-report for the sprint around it must list that PR as shipped with the same merge time, and must not
   count the follow-up PR that is still open;
3. pr-queue must flag the open follow-up PR (it has no reviewer), so the action item is not lost;
4. issue-triage over the same issues.json must not flag the closed incident issue.

The folder is assembled from the committed iteration and postmortem fixtures (synthetic data, example handles).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

from conftest import FIXTURES, ROOT

CLI = ROOT / "scripts" / "cli.py"


def gm(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, encoding="utf-8",
                          timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


def build_export(tmp_path):
    folder = tmp_path / "export"
    shutil.copytree(FIXTURES / "iteration", folder)
    for name in ("fixture-issue-412.json", "fixture-timeline-412.json"):
        shutil.copy(FIXTURES / "postmortem" / name, folder / name.replace("fixture-", ""))
    prs = json.loads((folder / "fixture-prs.json").read_text(encoding="utf-8"))
    prs += json.loads((FIXTURES / "postmortem" / "fixture-prs.json").read_text(encoding="utf-8"))
    (folder / "fixture-prs.json").write_text(json.dumps(prs), encoding="utf-8")
    issues = json.loads((folder / "fixture-issues.json").read_text(encoding="utf-8"))
    issues.append(json.loads((folder / "issue-412.json").read_text(encoding="utf-8")))
    (folder / "fixture-issues.json").write_text(json.dumps(issues), encoding="utf-8")
    (folder / "meta.json").write_text(json.dumps({"repo": "example-org/shop", "exported_at": "2026-09-26T09:00:00Z"}),
                                      encoding="utf-8")
    return folder


def test_incident_inside_a_sprint_agrees_across_skills(tmp_path):
    folder = build_export(tmp_path)

    rc, out, err = gm("postmortem", str(folder), "--issue", "412", "--json")
    assert rc == 0, err
    postmortem = json.loads(out)
    mitigated = next(p for p in postmortem["phases"] if p["phase"] == "mitigated")
    assert mitigated["cite"].startswith("PR #415 mergedAt")
    merged_in_timeline = {int(t["cite"].split()[1].lstrip("#")): t["time"] for t in postmortem["timeline"]
                          if t["cite"].startswith("PR #") and "mergedAt" in t["cite"]}
    assert merged_in_timeline == {409: "2026-09-19T16:00:00Z", 415: "2026-09-20T09:02:00Z"}

    rc, out, err = gm("iteration-report", str(folder), "--from", "2026-09-14", "--to", "2026-09-25", "--json")
    assert rc == 0, err
    report = json.loads(out)
    shipped = {row["number"]: row["merged"] for row in report["shipped"]}
    for number, merged in merged_in_timeline.items():
        assert shipped.get(number) == merged, f"PR #{number} is in the postmortem but not shipped in the report"
    assert 418 not in shipped

    rc, out, err = gm("pr-queue", str(folder), "--json")
    assert rc in (0, 1), err
    queue = json.loads(out)
    flagged = {row["pr"] for row in queue["findings"]} | {row["pr"] for row in queue["next_actions"]}
    assert 418 in flagged
    assert not {409, 415} & flagged

    rc, out, err = gm("issue-triage", str(folder), "--json")
    assert rc in (0, 1), err
    triage = json.loads(out)
    assert 412 not in {row["number"] for row in triage["issues"]}
