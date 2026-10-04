"""docs/demo.svg, the README demo, regenerates from the committed fixtures with scripts/render_demo.py.

The test renders into a temporary file and checks the result is well-formed SVG holding the command and lines of
its real output. It does not compare bytes with the committed SVG, so it stays stable across platforms.
"""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_demo.py"
SVG_NS = "{http://www.w3.org/2000/svg}"
COMMAND = "github-manager pr-queue tests/fixtures/pr_queue"
EXPECTED = "19 open PRs (2 drafts, 1 by bot accounts); 9 flagged; threshold 24h, stale drafts after 14d"


def svg_text(path: Path) -> str:
    """All text in the SVG, with the no-break spaces the renderer uses for runs of spaces turned back into spaces."""
    root = ET.parse(path).getroot()
    assert root.tag == f"{SVG_NS}svg"
    return "\n".join("".join(t.itertext()) for t in root.iter(f"{SVG_NS}text")).replace(" ", " ")


def test_render_demo_regenerates_a_well_formed_svg(tmp_path: Path) -> None:
    out = tmp_path / "demo.svg"
    result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(out)], cwd=ROOT, capture_output=True,
                            text=True, timeout=600)
    assert result.returncode == 0, result.stderr
    text = svg_text(out)
    assert f"$ {COMMAND}" in text
    assert EXPECTED in text
    assert "blocked-on-reviewer (1)" in text
    assert str(ROOT) not in text


def test_committed_demo_is_well_formed_and_matches_a_fresh_render(tmp_path: Path) -> None:
    committed = svg_text(ROOT / "docs" / "demo.svg")
    assert f"$ {COMMAND}" in committed
    out = tmp_path / "demo.svg"
    subprocess.run([sys.executable, str(SCRIPT), "--output", str(out)], cwd=ROOT, check=True, capture_output=True,
                   timeout=600)
    assert svg_text(out) == committed, "docs/demo.svg is out of date: run python3 scripts/render_demo.py"
