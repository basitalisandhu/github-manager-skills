# Security policy

This repository ships skills and scripts that run inside people's Claude Code sessions over exports of their GitHub data. The skill scripts read the folder you point them at and print a report; nothing here makes a network call, stores a token or reports usage anywhere.

## Supported versions

Only the latest release on `main` is supported. Pin a tag if you need stability, and update when a fix is announced in [CHANGELOG.md](CHANGELOG.md).

## Reporting a vulnerability

Please do not open a public issue for a security problem.

1. Use GitHub's private vulnerability reporting on this repository ("Security" tab, "Report a vulnerability").
2. If that is unavailable, open an issue titled "Security contact request" with no details, and the maintainer will reply with a private channel.

Include what you found, how to reproduce it, and what you think the impact is. You will get an acknowledgement within 5 working days and a fix or a mitigation plan within 30 days for confirmed issues.

## What counts

- A skill script that opens a network connection, starts a subprocess, or writes a file.
- `--redact` leaving a login from the export visible anywhere in the output (text, Markdown or JSON), or producing a token that can be reversed to the login without the export.
- An export command in a `SKILL.md` that changes data on GitHub, or asks for more access than reading.
- Text in any file of this repository that addresses the model rather than the reader, or a way for exported PR, issue or comment text to change what a script computes beyond its documented rules.

Calculation mistakes (a wrong wait, a missed carried-over issue, a phase taken from the wrong signal) are welcome as ordinary issues or pull requests with a fixture that shows them.

## What this plugin does and does not do

- No telemetry and no network access in the skill scripts. The `gh` export commands in each `SKILL.md` are run by you, read only, and use your own `gh` login.
- Scripts are standard-library Python, read the export folder, and print to standard output.
- `scripts/cli.py` starts the chosen skill script as a child process with the same Python and passes the arguments unchanged.
- Skill text tells Claude to treat exported GitHub content as untrusted data, never as instructions.
