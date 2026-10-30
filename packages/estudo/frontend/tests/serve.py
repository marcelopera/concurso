"""Start a temporary, isolated application for browser tests."""

import os
import tempfile
from pathlib import Path

from concurso_contracts.catalog.criar_demo import criar
from estudo.app import Application
from estudo.config import Settings
from estudo.initialization import prepare_study

ROOT = Path(__file__).resolve().parents[4]
with tempfile.TemporaryDirectory(prefix="concurso-e2e-") as tmp:
    os.environ["ESTUDO_DB"] = str(Path(tmp) / "estudo.sqlite")
    os.environ["ESTUDO_CONTENT_DB"] = str(Path(tmp) / "demo.sqlite")
    os.environ["ESTUDO_DIST_DIR"] = str(ROOT / "data/frontend")
    os.environ["ESTUDO_PLAN_FILE"] = str(ROOT / "plans/apofp-2026/roadmap.json")
    os.environ["ESTUDO_QUIET"] = "1"
    criar(Path(os.environ["ESTUDO_CONTENT_DB"]))
    app = Application(Settings.from_env())
    prepare_study(app)
    app.initialize()
    with app.http_server(("127.0.0.1", 8877)) as server:
        server.serve_forever()
