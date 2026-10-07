import subprocess
import sys

from conftest import ROOT


def test_repository_passes_its_own_validator():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_plugin.py")], capture_output=True,
                          text=True, timeout=120, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "4 skills, 0 error(s)" in proc.stdout
