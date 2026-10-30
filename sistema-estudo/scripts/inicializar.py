"""Initialize the default plan once, without replacing existing progress."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from preparar_container import prepare_study

if server.STUDY_DB.exists():
    print(f"Progresso existente preservado: {server.STUDY_DB}")
else:
    prepare_study()
