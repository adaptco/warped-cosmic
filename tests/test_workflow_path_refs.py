from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_references_resolve() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts/validate_workflow_paths.py")], check=True)
