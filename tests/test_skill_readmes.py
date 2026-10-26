"""Every skill has a README.md whose sample output is the real, current output of the command it names.

scripts/render_samples.py reruns each `<!-- sample: ... -->` command; run it without --check to refresh the READMEs
after changing a script's output.
"""
from __future__ import annotations

import subprocess
import sys

from conftest import ROOT, SKILLS


def test_every_skill_has_a_readme_with_a_sample():
    for skill in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        readme = skill / "README.md"
        assert readme.is_file(), f"{skill.name} has no README.md"
        text = readme.read_text(encoding="utf-8")
        assert text.startswith(f"# {skill.name}\n"), f"{readme} should start with '# {skill.name}'"
        assert "<!-- sample: " in text and "(SKILL.md)" in text, f"{readme} needs a sample block and a SKILL.md link"


def test_readme_samples_match_the_scripts():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "render_samples.py"), "--check"],
                          capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr + "\nrun python3 scripts/render_samples.py to refresh"
