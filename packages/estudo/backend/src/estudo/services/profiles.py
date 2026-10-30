"""Profile validation and request-local selection, independent of HTTP."""

import re
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from estudo.repositories import profiles as store

current = ContextVar("study_profile", default="principal")


def list_profiles(base):
    return store.list_profiles(base)


def create(base, name):
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 60:
        raise ValueError("Informe um nome de perfil com até 60 caracteres.")
    return store.create_profile(base, uuid.uuid4().hex, name.strip(), datetime.now(timezone.utc).isoformat())


def reset_roadmap(con, db_path):
    return store.reset_roadmap(con, db_path)


def database(base, profile_id):
    if profile_id == "principal":
        return base
    if not re.fullmatch(r"[a-f0-9]{32}", profile_id):
        raise ValueError("Perfil não encontrado. Selecione um perfil válido.")
    registered = store.registered(base, profile_id)
    if registered is None:
        raise ValueError("Perfil não encontrado. Selecione um perfil válido.")
    # Only the registered identifier contributes to the filename. Resolve and
    # check containment as well, so a database symlink cannot escape the folder.
    folder = (base.parent / (base.stem + "-perfis")).resolve()
    path = (folder / (registered["id"] + ".sqlite")).resolve()
    if not path.is_relative_to(folder) or not path.is_file():
        raise ValueError("O banco deste perfil não foi encontrado.")
    return path
