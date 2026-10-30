"""Validation of runtime plan packs before touching user progress."""

import json
import re
from datetime import date
from pathlib import Path


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise ValueError("Identificadores do plano devem ter até 100 letras ASCII, dígitos, hífen ou sublinhado.")


def load_plan(path: Path) -> dict:
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
        identifier(plan["id"])
        for key in ("title", "area", "strategy"):
            if not isinstance(plan[key], str) or not plan[key].strip():
                raise ValueError(f"Plano sem {key}.")
        date.fromisoformat(plan["exam_date"])
        date.fromisoformat(plan["coverage_deadline"])
        if type(plan["daily_minutes"]) is not int or plan["daily_minutes"] <= 0:
            raise ValueError("A duração diária precisa ser positiva.")
        lessons = []
        subjects = set()
        topic_owners = {}
        scheduled_dates = {}
        for subject in plan["subjects"]:
            if not all(isinstance(subject[k], str) and subject[k].strip() for k in ("subject_id", "name")):
                raise ValueError("Disciplina sem identificador ou nome.")
            identifier(subject["subject_id"])
            if subject["subject_id"] in subjects:
                raise ValueError("O plano contém disciplinas com identificadores repetidos.")
            subjects.add(subject["subject_id"])
            for unit in subject["lessons"]:
                for key in ("lesson_id", "topic_id", "topic", "title", "exam", "scheduled_date"):
                    if not isinstance(unit[key], str) or not unit[key].strip():
                        raise ValueError(f"Aula sem {key}.")
                date.fromisoformat(unit["scheduled_date"])
                identifier(unit["lesson_id"])
                identifier(unit["topic_id"])
                owner = (subject["subject_id"], unit["topic"])
                if topic_owners.setdefault(unit["topic_id"], owner) != owner:
                    raise ValueError("Um identificador de tópico foi reutilizado para outro conteúdo.")
                scheduled_dates[unit["lesson_id"]] = unit["scheduled_date"]
                if type(unit["minutes"]) is not int or unit["minutes"] <= 0:
                    raise ValueError("A duração da aula precisa ser positiva.")
                if "source_url" in unit and not unit["source_url"].startswith(("https://", "http://")):
                    raise ValueError("A fonte da aula deve usar HTTP ou HTTPS.")
                if not isinstance(unit.get("pages", []), list) or any(
                    type(p) is not int or p <= 0 for p in unit.get("pages", [])
                ):
                    raise ValueError("As páginas de uma aula devem ser números positivos.")
                lessons.append(unit["lesson_id"])
        if not lessons or len(set(lessons)) != len(lessons) or plan["coverage"]["lessons"] != len(lessons):
            raise ValueError("Quantidade de aulas inconsistente ou identificadores duplicados.")
        scheduled = []
        activities = []
        if not plan["days"]:
            raise ValueError("O calendário do plano está vazio.")
        days = set()
        for day in plan["days"]:
            date.fromisoformat(day["date"])
            if day["date"] in days or not isinstance(day["phase"], str):
                raise ValueError("O calendário contém dias repetidos ou fases inválidas.")
            days.add(day["date"])
            scheduled.extend(day["lessons"])
            if any(scheduled_dates.get(lesson_id) != day["date"] for lesson_id in day["lessons"]):
                raise ValueError("Uma aula está em um dia diferente da sua data agendada.")
            if not set(day.get("review_lesson_ids", [])) <= set(lessons):
                raise ValueError("Revisão aponta para aula ausente.")
            for activity in day["activities"]:
                if not all(isinstance(activity[k], str) for k in ("id", "title", "detail")):
                    raise ValueError("Atividade incompleta no calendário.")
                if type(activity["minutes"]) is not int or activity["minutes"] <= 0:
                    raise ValueError("A duração da atividade precisa ser positiva.")
                activities.append(activity["id"])
        if sorted(scheduled) != sorted(lessons) or len(set(activities)) != len(activities):
            raise ValueError("O calendário deve cobrir cada aula uma vez e usar atividades únicas.")
        return plan
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("Plano inválido: campos obrigatórios ausentes ou em formato incorreto.") from exc
