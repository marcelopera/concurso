"""Run installed-backend regressions against temporary synthetic data."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from concurso_contracts.catalog.criar_demo import criar

ROOT = Path(__file__).resolve().parents[4]
with tempfile.TemporaryDirectory(prefix="concurso-demo-") as tmp:
    catalog = Path(tmp) / "demo.sqlite"
    criar(catalog)
    env = dict(
        os.environ,
        ESTUDO_CONTENT_DB=str(catalog),
        ESTUDO_QUIET="1",
        ESTUDO_PLAN_FILE=str(ROOT / "plans/apofp-2026/roadmap.json"),
    )
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "unittest", "discover", "-s", str(Path(__file__).parent), "-v"], cwd=ROOT, env=env
        )
    )
