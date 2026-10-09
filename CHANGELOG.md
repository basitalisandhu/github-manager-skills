# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

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

[Unreleased]: https://github.com/basitalisandhu/github-manager-skills/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/basitalisandhu/github-manager-skills/releases/tag/v0.1.0
