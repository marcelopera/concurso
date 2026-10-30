"""Run an isolated demonstration server for browser tests."""

import os
import sys
import tempfile
from pathlib import Path

app = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app))
from catalogo.criar_demo import criar

with tempfile.TemporaryDirectory(prefix="concurso-e2e-") as tmp:
    os.environ["ESTUDO_DB"] = str(Path(tmp) / "estudo.sqlite")
    os.environ["ESTUDO_CONTENT_DB"] = str(Path(tmp) / "demo.sqlite")
    criar(Path(os.environ["ESTUDO_CONTENT_DB"]))
    import server
    from preparar_container import prepare_study

    prepare_study()
    sys.argv = ["server.py", "--port", "8877"]
    server.main()
