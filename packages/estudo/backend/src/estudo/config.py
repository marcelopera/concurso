"""Runtime paths and settings, resolved once per application instance."""

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
MAX_BODY = 22 * 1024 * 1024


@dataclass
class Settings:
    study_db: Path
    content_db: Path
    demo_content_db: Path
    library_root: Path
    dist_root: Path
    plan_file: Path | None
    port: int = 8765

    @classmethod
    def from_env(cls):
        data = Path(os.environ.get("ESTUDO_DATA_DIR", "data/estudo")).resolve()
        private = data / "conteudo.sqlite"
        demo = data / "demo.sqlite"
        return cls(
            study_db=Path(os.environ.get("ESTUDO_DB", data / "estudo.sqlite")).resolve(),
            content_db=Path(os.environ.get("ESTUDO_CONTENT_DB", private if private.is_file() else demo)).resolve(),
            demo_content_db=demo,
            library_root=Path(os.environ.get("BIBLIOTECA_DIR", "biblioteca-concursos")).resolve(),
            dist_root=Path(os.environ.get("ESTUDO_DIST_DIR", "data/frontend")).resolve(),
            plan_file=Path(os.environ["ESTUDO_PLAN_FILE"]).resolve() if os.environ.get("ESTUDO_PLAN_FILE") else None,
            port=int(os.environ.get("ESTUDO_PORT", "8765")),
        )


STEPS = (
    {"title": "Recuperar", "minutes": 10, "hint": "Escreva o que lembra. Sem consultar."},
    {"title": "Pré-teste", "minutes": 5, "hint": "Pode chutar. Só o gabarito aparece."},
    {"title": "Aula", "minutes": 20, "hint": "Estude no material. Anote só o que vale guardar."},
    {"title": "Whiteboard", "minutes": 10, "hint": "Reconstrua as relações de memória."},
    {"title": "Questões", "minutes": 15, "hint": "Comece com apoio. Termine sem."},
    {"title": "Fechar", "minutes": 3, "hint": "Confirme o que vale guardar."},
)
