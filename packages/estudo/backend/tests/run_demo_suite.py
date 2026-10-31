"""Run installed-backend regressions against temporary synthetic data."""

import os
import sys
import tempfile
import unittest
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
    os.environ.update(env)
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
