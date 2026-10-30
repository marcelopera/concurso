"""Prepare portable catalog paths and a fresh, populated study database at build time."""
import json
from pathlib import Path, PureWindowsPath
import sqlite3
import sys

app = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app))
import server
import roadmap
import map_questions


def prepare_catalog():
    with sqlite3.connect(server.CONTENT_DB) as con:
        for document_id, source in con.execute('SELECT documento_id, arquivo_local FROM documentos').fetchall():
            parts = PureWindowsPath(source).parts
            matches = [i for i, part in enumerate(parts) if part.lower() == 'biblioteca-concursos']
            if len(matches) != 1:
                raise ValueError(f'Caminho de documento não reconhecido: {document_id}')
            target = server.LIBRARY_ROOT.joinpath(*parts[matches[0] + 1:]).resolve()
            if not target.is_relative_to(server.LIBRARY_ROOT) or not target.is_file():
                raise ValueError(f'PDF ausente ou fora da biblioteca: {document_id}: {target}')
            con.execute('UPDATE documentos SET arquivo_local=? WHERE documento_id=?', (str(target), document_id))


def prepare_study():
    if server.STUDY_DB.exists():
        raise RuntimeError('O banco inicial já existe; recusei sobrescrevê-lo.')
    server.init_db()
    roadmap.install(server.STUDY_DB)
    mapping = app / 'roadmaps' / 'apofp-2026' / 'vinculacao'
    links = [json.loads(line) for line in (mapping / 'vinculos.jsonl').read_text(encoding='utf-8').splitlines() if line]
    report = json.loads((mapping / 'relatorio.json').read_text(encoding='utf-8'))
    map_questions.apply_links(links, report, server.STUDY_DB)
    with sqlite3.connect(server.STUDY_DB) as con:
        assert con.execute('SELECT count(*) FROM plan_units').fetchone()[0] == 94
        assert con.execute('SELECT count(*) FROM lesson_questions').fetchone()[0] == len(links)
        assert not con.execute('PRAGMA foreign_key_check').fetchall()
    for backup in server.STUDY_DB.parent.glob('estudo-antes-*.sqlite'):
        backup.unlink()


if __name__ == '__main__':
    prepare_catalog()
    prepare_study()
