# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

## [0.4.0] - 2026-10-26

### Added

- `iteration-report` lists scope added or removed during the window (#3). With `timeline-<N>.json` files in the export, `milestoned` and `demilestoned` events for the scope milestone inside the window appear as "Added to scope during the window" and "Removed from scope during the window", each citing its event id (or the file and row when the event has none), and the summary says how many were added and removed. Without timeline files, or when the scope is not a milestone, the report says scope changes were not measured. SKILL.md has the export loop; three fixture timelines and seven tests cover it.
- A README in every skill folder with a real sample produced by running the script on its fixture. `scripts/render_samples.py` refreshes them and `tests/test_skill_readmes.py` fails when a sample no longer matches the script.
- `tests/test_fuzz_inputs.py`: seeded fuzzing of every export each script reads (values swapped for other JSON types, keys dropped, lists emptied or wrapped, files truncated) and of the YAML keyword map. Replay a failure with `FUZZ_SEED`, run longer with `FUZZ_ROUNDS`.
- `tests/test_integration_chain.py`: one export folder for an incident inside a sprint, run through all four subcommands of the dispatcher; the postmortem's merged PRs must be shipped in the iteration report with the same merge times, and the open follow-up PR must be flagged by the PR queue.

### Fixed

- Hand-edited or unusual exports no longer crash with a traceback. The fuzzer found 22 places where a field of the wrong JSON type (a number for a title, an object for a body, a string for a list of labels, reviews or comments, a list for a milestone title, a non-numeric thumbs-up count, an object for `meta.json` repo) raised `TypeError`, `AttributeError` or `ValueError`. Such fields are now read as empty through shared `text_of`, `list_of` and `dict_of` helpers, so the scripts report what they can; malformed numbers and times still exit 2 as before.
- `--redact` was quadratic: it ran one regular expression per login over every text, so its cost grew with texts times logins. It now makes one pass per text and looks each word up in a table; output is byte for byte the same. On inputs 100 times the fixtures, `postmortem.py --redact` went from 3.22s to 0.13s, `pr_queue.py --redact` from 1.14s to 0.09s and `iteration_report.py --redact` from 0.77s to 0.08s. A test compares it with the old method on random text and fails if it slows down again.

### Changed

- `iteration-report` description quotes "write the iteration report" and names merged and slipped work; `incident-postmortem-timeline` description points sprint reports at `iteration-report` (its "incidents with no GitHub issue" note moved to Limits). A lexical trigger check across the four skills (20 should-trigger, 60 should-not-trigger prompts in cross mode) went from 2 missed and 1 false trigger to none.
- Version 0.4.0 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher and the README container examples.

## [0.3.1] - 2026-10-18

### Fixed

- A malformed export no longer crashes or passes silently. A `number` that is not a whole number crashed `pr_queue.py`, `iteration_report.py` and `postmortem.py` with a traceback and exit 1, which a scheduled job reads as "flagged"; a `createdAt` that was missing or not an ISO time made `pr_queue.py` and `iteration_report.py` report "0 flagged" for a PR they could not read. All four scripts now check every row through the shared `check_rows` helper and exit 2 with the file, the row and the export command to re-run. A garbled `mergedAt`, `closedAt` or `updatedAt` is bad input too; null stays allowed.
- An empty export file now says "the file is empty" instead of a JSON decoder message, and a timeline or PR file holding an object (for example a `gh api` error body) names the file and says it found an object.
- `pr_queue.py` exits 2 when `meta.json` is not an object (it was ignored silently), and `issue_triage.py` names the meta file it read (it always printed `meta.json`, also for `fixture-meta.json`).

### Added

- A committed issue triage fixture (`tests/fixtures/issue_triage`, six synthetic issues with planted unlabelled, unanswered, bot-only, duplicate, stale and popular cases and a JSON keyword map), run in CI with its expected exit 1, and in the README quick start.
- `tests/test_malformed_inputs.py`: empty file, CSV instead of JSON, object instead of list, a non-numeric or boolean `number`, unparseable `createdAt`, `mergedAt` and timeline bodies, across all four scripts (36 cases), and five tests over the committed triage fixture. 143 tests before, 184 after.
- README: one exit code table for all scripts, and real sample output for `issue-triage`, `iteration-report` and `postmortem`; each SKILL.md states the same exit codes and what bad input covers.

### Changed

- `pr-queue-digest` description quotes "which approved PRs are not merged yet?" and points open issues at `issue-triage-digest`; `issue-triage-digest` description leads with the goal rather than the script and quotes "what has nobody answered?".
- Version 0.3.1 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher and the README container examples.

## [0.3.0] - 2026-10-09

### Added

- Check draft postmortem table times against exported timeline rows, with line
  numbers and a one-minute tolerance.

## [0.2.0] - 2026-10-05

### Added

- `issue-triage-digest`: `issue_triage.py` reads a saved `gh issue list --json` export and flags unlabelled issues, issues with no reply from anyone but the author for `--unanswered-days`, possible duplicates by title word overlap (`--similarity`), stale issues (`--stale-days`) and issues with at least `--reactions` thumbs-up; suggests labels per issue from a YAML or JSON keyword map (`--keywords`); prints text, Markdown or JSON, or writes `issue-triage.md` and `issue-triage.json` with `--out`; counts per check and per label only; exit 1 when anything is flagged.
- `github-manager issue-triage` subcommand in the dispatcher, the container image and the Python package.

### Changed

- Version 0.2.0 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher and the README container examples. The READMEs no longer say issue triage is out of scope.

## [0.1.2] - 2026-10-05

### Changed

- Rewrote all three skill descriptions to 463 to 513 characters (from 820 to 887): each starts with a verb, states the goal before the mechanism, carries one quoted phrase a user would type, a "Use when ..." sentence and a "Not for ..." boundary, and stays double-quoted.
- `iteration-report` states its boundary with `weekly-status-rollup` (ways-of-working-skills) and `incident-postmortem-timeline` with `postmortem-writer` (claude-dev-skills).
- Tests open text files with `encoding="utf-8"` (the scripts already did), and CI runs tests and ruff on `windows-latest` as well as Ubuntu and macOS.
- The plugin and root READMEs mention stale PRs, the DORA metrics (only lead time up to the merge is computed) and issue triage (not covered).
- `scripts/validate_plugin.py` now fails when a description is over 600 characters, is not double-quoted, or lacks "Use " or "Not for"; `tests/test_skill_frontmatter.py` covers each rule and the existing `## Limits` requirement.
- Version 0.1.2 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher and the README container examples.

## [0.1.1] - 2026-10-04

### Fixed

- Quoted SKILL.md descriptions that contained a colon so the frontmatter parses under strict YAML readers such as the skills CLI; the validator now fails on unquoted scalars with ': ' or ' #'.

## [0.1.0] - 2026-10-04

### Added

- Plugin marketplace `github-manager-skills` with one plugin, `github-manager`, and three skills, each with a tested standard-library script that reads saved `gh` exports and never calls the network.
- `pr-queue-digest`: `pr_queue.py` flags PRs waiting on review longer than `--hours` (measured from the review request event when a timeline file is exported), PRs blocked on one requested reviewer with at least `--reviewer-load` other pending requests, changes requested with no new commits, commits after a changes request with no re-request, failing checks, merge conflicts, approved but unmerged PRs, PRs with no reviewer and stale drafts; prints a review-queue table per reviewer (counts only, sorted by name) and one next action per PR; text, Markdown or JSON; exit 1 when anything is flagged.
- `iteration-report`: `iteration_report.py` reports, for a window of whole UTC days, shipped PRs with the issues they close, scope (a milestone, or open assigned issues), completed, not planned, carried over, newly opened, PRs merged outside the window and closed unmerged, cycle time median and nearest-rank p90 from first commit or PR creation, and review turnaround median; every number followed by its rows; team level only.
- `incident-postmortem-timeline`: `postmortem.py` builds a timeline from an incident issue export (labels, assignments, comments, cross-references, linked PR merges, closes), derives detected, acknowledged, mitigated and resolved by stated rules, reports signals that disagree, lists people as roles, writes contributing factors as questions, and prints a postmortem skeleton citing each row to its event id, comment id or PR.
- `--redact` on every script: logins become stable `user-xxxxxx` tokens, or roles in the postmortem.
- `scripts/cli.py`: the `github-manager <subcommand>` dispatcher (`pr-queue`, `iteration-report`, `postmortem`), used by the container image and the Python package.
- `scripts/validate_plugin.py`, `scripts/render_demo.py` and `docs/demo.svg`; fixtures with planted cases; pytest suite; CI on Python 3.11 to 3.13 on Linux and macOS, a container build check and `claude plugin validate --strict`.
- `Dockerfile` and `publish-github-packages.yml`: on a `v*` tag, the image `ghcr.io/basitalisandhu/github-manager-skills` for linux/amd64 and linux/arm64 with an SPDX SBOM, a build provenance attestation and a keyless cosign signature.
- `release.yml`: PyPI trusted publishing of the `github-manager-skills` package, off until the repository variable `PYPI_PUBLISH` is `true`.
- Six tasks in `docs/good-first-issues.md`.

[Unreleased]: https://github.com/basitalisandhu/github-manager-skills/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/basitalisandhu/github-manager-skills/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/basitalisandhu/github-manager-skills/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/basitalisandhu/github-manager-skills/compare/v0.2.0...v0.3.0
[0.1.0]: https://github.com/basitalisandhu/github-manager-skills/releases/tag/v0.1.0
