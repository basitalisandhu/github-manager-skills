# Good first issues

Small, well-specified pieces of work for a first contribution. Each is self-contained, comes with the test to add, and needs no account, token or network access: the fixtures are saved exports. Read [CONTRIBUTING.md](../CONTRIBUTING.md) first: standard library only, a planted case in a `fixture-*.json` file with every rule change, example handles only, no per-person scoring, plain language without em-dashes.

To claim one, open an issue with the title below (or comment on the existing one) and say you are working on it. Run `python3 -m pytest -q`, `ruff check .` and `python3 scripts/validate_plugin.py` before opening the pull request.

## 1. pr-queue-digest: count working hours only with `--business-hours`

**Labels:** good first issue, pr-queue-digest, python

**Context.** A PR opened on Friday evening shows a 60-hour wait on Monday morning. Teams that review only on working days want the wait measured in working hours.

**Acceptance criteria.**
- `--business-hours 09:00-17:00` and `--workdays mon-fri` (both optional, UTC unless `--tz-offset +05:00` is given) make every wait in `pr_queue.py` count only time inside those hours.
- The output states the basis ("working hours, 09:00-17:00 Mon-Fri, UTC+05:00") next to the threshold.
- A test with a PR requested on Friday 16:00 and an "as of" time of Monday 10:00 expects 2 working hours.

## 2. pr-queue-digest: split bot-authored PRs into their own section

**Labels:** good first issue, pr-queue-digest, python

**Context.** The summary counts PRs by bot accounts, but dependency and agent PRs are mixed into the findings. Leads facing many agent-authored PRs want to see them apart.

**Acceptance criteria.**
- `--split-bots` groups findings and next actions into "people" and "bot accounts" sections (same rules, no change in exit code).
- `is_bot` stays the single definition (`is_bot` flag, `type == "Bot"`, a login ending in `[bot]`).
- A fixture PR from `renovate[bot]` with failing checks appears only in the bot section.

## 3. iteration-report: detect scope added or removed during the window

**Labels:** good first issue, iteration-report, python

**Context.** Milestone membership is read as it is at export time, so an issue added to the milestone halfway through the sprint looks as if it was planned from the start.

**Acceptance criteria.**
- When `timeline-<N>.json` files exist for scope issues, `milestoned` and `demilestoned` events inside the window are listed as "added during the window" and "removed during the window", each citing the event id.
- The summary line for scope says how many were added and removed.
- Fixture timelines for one added and one removed issue, with a test for each.

## 4. iteration-report: read GitHub Projects iteration fields

**Labels:** good first issue, iteration-report, python

**Context.** Teams that plan with Projects iterations rather than milestones cannot set the scope today.

**Acceptance criteria.**
- Document a `gh project item-list <number> --owner OWNER --format json` export in `SKILL.md`.
- `--iteration "Iteration 12"` selects scope issues whose iteration field matches, read from `project-items.json`.
- A fixture with two iterations and a test that the scope and carried-over lists follow the chosen one.

## 5. incident-postmortem-timeline: add workflow runs as deploy signals

**Labels:** good first issue, incident-postmortem-timeline, python

**Context.** A PR merge is not a deploy. When a deploy workflow ran after the mitigation PR merged, that run is a better "mitigated" signal.

**Acceptance criteria.**
- Optional `runs.json` from `gh run list --workflow deploy.yml --json databaseId,headSha,conclusion,createdAt,updatedAt,url`.
- A successful run whose `headSha` matches a mitigation PR's merge commit becomes a timeline row and a "mitigated" signal citing the run id; the gap between merge and deploy is reported under "Signals that disagree".
- A fixture run and a test.

## 6. incident-postmortem-timeline: check an existing postmortem draft against the timeline

**Labels:** good first issue, incident-postmortem-timeline, python

**Context.** Teams often have a draft written by hand. Each time in it should match a cited row.

**Acceptance criteria.**
- `--check draft.md` reads `HH:MM` and ISO times from table rows in the draft and reports each one that matches no timeline row within one minute, with the draft's line number.
- Exit code 1 when any time is unmatched, 0 otherwise.
- A fixture draft with one wrong time and a test that only that line is reported.
