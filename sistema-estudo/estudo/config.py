"""Configuration shared by the study server and its clients."""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent
DATA_DIR = APP_ROOT / "dados"
PRIVATE_CONTENT_DB = DATA_DIR / "conteudo.sqlite"
DEMO_CONTENT_DB = DATA_DIR / "demo.sqlite"
CONTENT_DB = Path(
    os.environ.get("ESTUDO_CONTENT_DB", PRIVATE_CONTENT_DB if PRIVATE_CONTENT_DB.is_file() else DEMO_CONTENT_DB)
).resolve()
STUDY_DB = Path(os.environ.get("ESTUDO_DB", DATA_DIR / "estudo.sqlite")).resolve()
LIBRARY_ROOT = Path(os.environ.get("BIBLIOTECA_DIR", REPO_ROOT / "biblioteca-concursos")).resolve()
DIST_ROOT = APP_ROOT / "dist"
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
PORT = int(os.environ.get("ESTUDO_PORT", "8765"))
MAX_BODY = 22 * 1024 * 1024

STEPS = (
    {"title": "Recuperar", "minutes": 10, "hint": "Escreva o que lembra. Sem consultar."},
    {"title": "Pré-teste", "minutes": 5, "hint": "Pode chutar. Só o gabarito aparece."},
    {"title": "Aula", "minutes": 20, "hint": "Estude no material. Anote só o que vale guardar."},
    {"title": "Whiteboard", "minutes": 10, "hint": "Reconstrua as relações de memória."},
    {"title": "Questões", "minutes": 15, "hint": "Comece com apoio. Termine sem."},
    {"title": "Fechar", "minutes": 3, "hint": "Confirme o que vale guardar."},
)
