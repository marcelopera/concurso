"""Persistent, additive study plans layered over the existing lessons and sessions."""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

from estudo.config import Settings
from estudo.db.migrations import migrate
from estudo.errors import DomainError
from estudo.plans import load_plan
from estudo.repositories import plans as store
from estudo.services import profiles

PLAN_FILE = Settings.from_env().plan_file


def init_schema(con):
    migrate(con)


def lesson_metadata(con, lesson_id):
    row = store.lesson_metadata(con, (lesson_id,))
    return json.loads(row[0]) if row else None


def public_plan(con, today):
    row = store.latest_config(con)
    if not row:
        return None
    plan = json.loads(row[0])
    question_counts = {r[0]: r[1] for r in store.question_counts(con)}
    units = {}
    for r in store.units(con, (plan["id"],)):
        meta = json.loads(r["metadata_json"])
        units[r["lesson_id"]] = dict(
            id=r["lesson_id"],
            title=r["title"],
            completed_at=r["completed_at"],
            topic_title=r["topic_title"],
            subject_name=r["subject_name"],
            scheduled_date=meta["scheduled_date"],
            exam=meta["exam"],
            minutes=meta["minutes"],
            question_count=question_counts.get(r["lesson_id"], 0),
        )
    progress = {
        r["activity_id"]: dict(completed_at=r["completed_at"], note=r["note"])
        for r in store.activity_progress(con, (plan["id"],))
    }
    for day in plan["days"]:
        day["lessons"] = [units[lid] for lid in day["lessons"] if lid in units]
        day["review_lessons"] = [units[lid] for lid in day.pop("review_lesson_ids", []) if lid in units]
        for activity in day["activities"]:
            activity.update(progress.get(activity["id"], dict(completed_at=None, note="")))
    completed = sum((bool(u["completed_at"]) for u in units.values()))
    overdue = [u for u in units.values() if u["scheduled_date"] < today and (not u["completed_at"])]
    upcoming = sorted(
        (u for u in units.values() if not u["completed_at"]), key=lambda u: (u["scheduled_date"], u["id"])
    )
    plan["stats"] = dict(
        lessons=len(units),
        completed=completed,
        overdue=len(overdue),
        days_remaining=max(0, (date.fromisoformat(plan["exam_date"]) - date.fromisoformat(today)).days),
        total_hours=len(plan["days"]) * plan["daily_minutes"] // 60,
        completed_activities=sum((bool(p["completed_at"]) for p in progress.values())),
    )
    plan["next_lesson"] = upcoming[0] if upcoming else None
    plan["today"] = today
    plan["overdue_lessons"] = sorted(overdue, key=lambda u: (u["scheduled_date"], u["id"]))
    return plan


def update_activity(con, activity_id, body):
    row = store.latest_plan(con)
    if not row:
        raise ValueError("Nenhum plano cadastrado.")
    config = json.loads(row["config_json"])
    if activity_id not in {a["id"] for d in config["days"] for a in d["activities"]}:
        raise ValueError("Atividade não encontrada no plano.")
    if type(body.get("completed")) is not bool:
        raise ValueError("Informe se a atividade foi concluída.")
    note = body.get("note", "")
    if not isinstance(note, str) or len(note) > 4000:
        raise ValueError("A anotação deve ter até 4000 caracteres.")
    completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if body["completed"] else None
    store.save_activity(con, (row["plan_id"], activity_id, completed_at, note.strip()))
    return dict(completed_at=completed_at, note=note.strip())


def install(db_path, plan_file=None):
    plan = load_plan(plan_file or PLAN_FILE)
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise ValueError("Inicialize o banco pelo servidor antes de importar o plano.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    backup = db_path.with_name("estudo-antes-roadmap-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".sqlite")
    with closing(sqlite3.connect(db_path)) as con:
        store.enable_foreign_keys(con)
        with closing(sqlite3.connect(backup)) as dest:
            con.backup(dest)
        init_schema(con)
        store.begin_write(con)
        before = store.lesson_count(con)[0]
        config = {k: v for k, v in plan.items() if k != "subjects"}
        config["subject_info"] = [
            {k: v for k, v in s.items() if k not in ["lessons", "source_text"]} for s in plan["subjects"]
        ]
        existing = store.plan_config(con, (plan["id"],))
        if existing and json.loads(existing[0]) != config:
            raise ValueError(
                "O identificador deste plano já existe com outra configuração. Use um novo ID para outra versão."
            )
        store.insert_plan(con, (plan["id"], json.dumps(config, ensure_ascii=False), now))
        for subject in plan["subjects"]:
            sid = subject["subject_id"]
            store.insert_subject(con, (sid, subject["name"], now))
            actual_subject = store.subject_by_name(con, (subject["name"],))
            if actual_subject is None:
                raise ValueError("O identificador da disciplina já pertence a outro nome.")
            actual_sid = actual_subject[0]
            topics = {}
            for unit in subject["lessons"]:
                topic_key = unit["topic_id"]
                if topic_key not in topics:
                    store.insert_topic(con, (topic_key, actual_sid, unit["topic"], len(topics), now))
                    actual_topic = store.topic_by_title(con, (actual_sid, unit["topic"]))
                    if actual_topic is None:
                        raise ValueError("O identificador do tópico já pertence a outra disciplina ou título.")
                    topics[topic_key] = actual_topic[0]
                owner = store.other_owner(con, (unit["lesson_id"], plan["id"]))
                current_lesson = store.lesson_topic(con, (unit["lesson_id"],))
                if owner or (current_lesson and current_lesson[0] != topics[topic_key]):
                    raise ValueError("O identificador de uma aula já pertence a outro plano ou tópico.")
                metadata = store.unit_metadata(con, (plan["id"], unit["lesson_id"]))
                if metadata and json.loads(metadata[0]) != unit:
                    raise ValueError("Os metadados desta aula mudaram. Use um novo identificador de plano.")
                store.insert_lesson(con, (unit["lesson_id"], topics[topic_key], unit["title"], now))
                store.insert_unit(con, (plan["id"], unit["lesson_id"], json.dumps(unit, ensure_ascii=False)))
                material_id = "source_" + unit["lesson_id"]
                if not unit.get("source_url"):
                    continue
                page = unit.get("pages", [])[0] if unit.get("pages") else None
                store.insert_material(
                    con,
                    (
                        material_id,
                        unit["lesson_id"],
                        "Fonte do plano" + (" · página " + str(page) if page else ""),
                        unit["source_url"] + ("#page=" + str(page) if page else ""),
                        0,
                        now,
                    ),
                )
        count = store.unit_count(con, (plan["id"],))[0]
        if count != plan["coverage"]["lessons"]:
            raise RuntimeError("O plano importado não contém a quantidade esperada de aulas.")
        if store.foreign_key_errors(con):
            raise RuntimeError("O plano importado contém referências inválidas.")
        con.commit()
        print(
            json.dumps(
                dict(plan=plan["id"], lessons=count, added=store.lesson_count(con)[0] - before, backup=str(backup)),
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install",
        type=Path,
        required=True,
        help="Existing study database; makes an SQLite backup before additive import.",
    )
    parser.add_argument(
        "--plan", type=Path, help="Arquivo JSON do plano; padrão: ESTUDO_PLAN_FILE ou plano demonstrativo."
    )
    args = parser.parse_args()
    install(args.install, args.plan)


def reset(app, body):
    if body.get("confirm") != profiles.current.get():
        raise DomainError("Confirme o perfil para resetar o roadmap.")
    with app.study_db() as con:
        result = profiles.reset_roadmap(con, profiles.database(app.settings.study_db, profiles.current.get()))
        con.commit()
    return result


def save_activity(app, activity_id, body):
    with app.study_db() as con:
        result = update_activity(con, activity_id, body)
        con.commit()
    return result
