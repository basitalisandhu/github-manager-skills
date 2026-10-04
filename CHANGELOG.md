# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

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
