"""Run Python tests against an isolated synthetic catalog, even when private data exists."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

app = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app))
from catalogo.criar_demo import criar

with tempfile.TemporaryDirectory(prefix="concurso-demo-") as tmp:
    catalog = Path(tmp) / "demo.sqlite"
    criar(catalog)
    env = dict(os.environ, ESTUDO_CONTENT_DB=str(catalog), ESTUDO_QUIET="1")
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "unittest", "discover", "-s", str(app / "tests"), "-v"], cwd=app, env=env
        )
    )
