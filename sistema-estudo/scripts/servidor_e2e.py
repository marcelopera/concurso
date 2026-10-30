"""Run an isolated demonstration server for browser tests."""
import os
from pathlib import Path
import sys
import tempfile

app = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app))
from catalogo.criar_demo import criar

with tempfile.TemporaryDirectory(prefix='concurso-e2e-') as tmp:
    os.environ['ESTUDO_DB'] = str(Path(tmp) / 'estudo.sqlite')
    os.environ['ESTUDO_CONTENT_DB'] = str(Path(tmp) / 'demo.sqlite')
    criar(Path(os.environ['ESTUDO_CONTENT_DB']))
    from preparar_container import prepare_study
    import server
    prepare_study()
    sys.argv = ['server.py', '--port', '8877']
    server.main()
