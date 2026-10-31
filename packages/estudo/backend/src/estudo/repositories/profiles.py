"""Profile registry, isolated progress cloning and scoped reset persistence."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone


def registry(base):
    con = sqlite3.connect(base.with_name(base.stem + "-perfis.sqlite"), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE,
        created_at TEXT NOT NULL)
        """
    )
    con.execute(
        "INSERT OR IGNORE INTO profiles VALUES(?,?,?)",
        ("principal", "Principal", datetime.now(timezone.utc).isoformat()),
    )
    con.commit()
    return con


def list_profiles(base):
    with closing(registry(base)) as con:
        return [dict(r) for r in con.execute("SELECT * FROM profiles ORDER BY created_at,id")]


def reset_roadmap(con, db_path):
    row = con.execute("SELECT plan_id FROM study_plans ORDER BY created_at DESC,rowid DESC LIMIT 1").fetchone()
    if row is None:
        raise ValueError("Nenhum roadmap cadastrado.")
    plan_id = row[0]
    backup = db_path.with_name(db_path.stem + "-antes-reset-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".sqlite")
    # Lock out writes until the backup and the reset have both finished.
    con.execute("BEGIN IMMEDIATE")
    with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(backup)) as dest:
        source.backup(dest)
    lessons = "SELECT lesson_id FROM plan_units WHERE plan_id=?"
    sessions = "SELECT session_id FROM study_sessions WHERE lesson_id IN (" + lessons + ")"
    con.execute("DELETE FROM cards WHERE source_session_id IN (" + sessions + ")", (plan_id,))
    con.execute("DELETE FROM attempts WHERE session_id IN (" + sessions + ")", (plan_id,))
    con.execute("DELETE FROM study_sessions WHERE lesson_id IN (" + lessons + ")", (plan_id,))
    con.execute("UPDATE lessons SET completed_at=NULL WHERE lesson_id IN (" + lessons + ")", (plan_id,))
    con.execute("DELETE FROM plan_activity_progress WHERE plan_id=?", (plan_id,))
    return dict(ok=True, backup=backup.name)


def create_profile(base, profile_id, name, created_at):
    folder = base.parent / (base.stem + "-perfis")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (profile_id + ".sqlite")
    with closing(registry(base)) as meta:
        meta.execute("BEGIN IMMEDIATE")
        if meta.execute("SELECT 1 FROM profiles WHERE name=? COLLATE NOCASE", (name,)).fetchone():
            raise ValueError("Já existe um perfil com esse nome.")
        try:
            with closing(sqlite3.connect(base)) as source, closing(sqlite3.connect(path)) as dest:
                source.backup(dest)
                dest.execute("PRAGMA foreign_keys=ON")
                with dest:
                    for table in (
                        "card_reviews",
                        "cards",
                        "attempts",
                        "lesson_difficulties",
                        "study_sessions",
                        "plan_activity_progress",
                    ):
                        dest.execute("DELETE FROM " + table)
                    dest.execute("UPDATE lessons SET completed_at=NULL")
            meta.execute("INSERT INTO profiles VALUES(?,?,?)", (profile_id, name, created_at))
            meta.commit()
        except Exception:
            path.unlink(missing_ok=True)
            raise
    return dict(id=profile_id, name=name, created_at=created_at)


def registered(base, profile_id):
    with closing(registry(base)) as con:
        return con.execute("SELECT id FROM profiles WHERE id=?", (profile_id,)).fetchone()
