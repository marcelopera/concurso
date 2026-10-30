"""Persistent, additive study plans layered over the existing lessons and sessions."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3

PLAN_FILE = Path(__file__).parent / 'roadmaps' / 'apofp-2026' / 'roadmap.json'


def init_schema(con):
    con.executescript('''
        CREATE TABLE IF NOT EXISTS study_plans (
            plan_id TEXT PRIMARY KEY,
            config_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS plan_units (
            plan_id TEXT NOT NULL REFERENCES study_plans(plan_id),
            lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id),
            metadata_json TEXT NOT NULL,
            PRIMARY KEY(plan_id, lesson_id)
        );
        CREATE TABLE IF NOT EXISTS plan_activity_progress (
            plan_id TEXT NOT NULL REFERENCES study_plans(plan_id),
            activity_id TEXT NOT NULL,
            completed_at TEXT,
            note TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(plan_id, activity_id)
        );
    ''')


def lesson_metadata(con, lesson_id):
    row = con.execute('SELECT metadata_json FROM plan_units WHERE lesson_id=?', (lesson_id,)).fetchone()
    return json.loads(row[0]) if row else None


def public_plan(con, today):
    row = con.execute('SELECT config_json FROM study_plans ORDER BY created_at DESC LIMIT 1').fetchone()
    if not row:
        return None
    plan = json.loads(row[0])
    question_counts = {r[0]:r[1] for r in con.execute('SELECT lesson_id,count(*) FROM lesson_questions GROUP BY lesson_id')}
    units = {}
    for r in con.execute('''SELECT u.metadata_json, l.lesson_id, l.title, l.completed_at,
                                  t.title AS topic_title, s.name AS subject_name
                           FROM plan_units u JOIN lessons l USING(lesson_id)
                           JOIN topics t USING(topic_id) JOIN subjects s USING(subject_id)
                           WHERE u.plan_id=?''', (plan['id'],)):
        meta = json.loads(r['metadata_json'])
        units[r['lesson_id']] = dict(id=r['lesson_id'], title=r['title'], completed_at=r['completed_at'],
                                    topic_title=r['topic_title'], subject_name=r['subject_name'],
                                    scheduled_date=meta['scheduled_date'], exam=meta['exam'], minutes=meta['minutes'],
                                    question_count=question_counts.get(r['lesson_id'],0))
    progress = {r['activity_id']: dict(completed_at=r['completed_at'], note=r['note'])
                for r in con.execute('SELECT * FROM plan_activity_progress WHERE plan_id=?',(plan['id'],))}
    for day in plan['days']:
        day['lessons'] = [units[lid] for lid in day['lessons'] if lid in units]
        day['review_lessons'] = [units[lid] for lid in day.pop('review_lesson_ids',[]) if lid in units]
        for activity in day['activities']:
            activity.update(progress.get(activity['id'],dict(completed_at=None,note='')))
    completed = sum(bool(u['completed_at']) for u in units.values())
    overdue = [u for u in units.values() if u['scheduled_date']<today and not u['completed_at']]
    upcoming = sorted((u for u in units.values() if not u['completed_at']),key=lambda u:(u['scheduled_date'],u['id']))
    plan['stats'] = dict(lessons=len(units),completed=completed,overdue=len(overdue),
                         days_remaining=max(0,(date.fromisoformat(plan['exam_date'])-date.fromisoformat(today)).days),
                         total_hours=len(plan['days'])*plan['daily_minutes']//60,
                         completed_activities=sum(bool(p['completed_at']) for p in progress.values()))
    plan['next_lesson'] = upcoming[0] if upcoming else None
    plan['today'] = today
    plan['overdue_lessons'] = sorted(overdue,key=lambda u:(u['scheduled_date'],u['id']))
    return plan


def update_activity(con, activity_id, body):
    row = con.execute('SELECT plan_id,config_json FROM study_plans ORDER BY created_at DESC LIMIT 1').fetchone()
    if not row:
        raise ValueError('Nenhum plano cadastrado.')
    config = json.loads(row['config_json'])
    if activity_id not in {a['id'] for d in config['days'] for a in d['activities']}:
        raise ValueError('Atividade não encontrada no plano.')
    if type(body.get('completed')) is not bool:
        raise ValueError('Informe se a atividade foi concluída.')
    note = body.get('note','')
    if not isinstance(note,str) or len(note)>4000:
        raise ValueError('A anotação deve ter até 4000 caracteres.')
    completed_at = datetime.now(timezone.utc).isoformat(timespec='seconds') if body['completed'] else None
    con.execute('''INSERT INTO plan_activity_progress(plan_id,activity_id,completed_at,note) VALUES(?,?,?,?)
                   ON CONFLICT(plan_id,activity_id) DO UPDATE SET completed_at=excluded.completed_at,note=excluded.note''',
                (row['plan_id'],activity_id,completed_at,note.strip()))
    return dict(completed_at=completed_at,note=note.strip())


def install(db_path):
    plan = json.loads(PLAN_FILE.read_text(encoding='utf-8'))
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise ValueError('Inicialize o banco pelo servidor antes de importar o plano.')
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    backup = db_path.with_name('estudo-antes-roadmap-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite')
    with closing(sqlite3.connect(db_path)) as con:
        con.execute('PRAGMA foreign_keys=ON')
        with closing(sqlite3.connect(backup)) as dest:
            con.backup(dest)
        init_schema(con)
        before = con.execute('SELECT count(*) FROM lessons').fetchone()[0]
        config = {k:v for k,v in plan.items() if k!='subjects'}
        config['subject_info'] = [{k:v for k,v in s.items() if k not in ['lessons','source_text']} for s in plan['subjects']]
        con.execute('INSERT OR IGNORE INTO study_plans VALUES(?,?,?)',(plan['id'],json.dumps(config,ensure_ascii=False),now))
        for subject in plan['subjects']:
            sid = subject['subject_id']
            con.execute('INSERT OR IGNORE INTO subjects VALUES(?,?,?)',(sid,subject['name'],now))
            actual_sid = con.execute('SELECT subject_id FROM subjects WHERE name=? COLLATE NOCASE',(subject['name'],)).fetchone()[0]
            topics = {}
            for unit in subject['lessons']:
                topic_key = unit['topic_id']
                if topic_key not in topics:
                    con.execute('INSERT OR IGNORE INTO topics VALUES(?,?,?,?,?)',
                                (topic_key,actual_sid,unit['topic'],len(topics),now))
                    topics[topic_key] = con.execute('SELECT topic_id FROM topics WHERE subject_id=? AND title=?',
                                                   (actual_sid,unit['topic'])).fetchone()[0]
                con.execute('INSERT OR IGNORE INTO lessons(lesson_id,topic_id,title,created_at) VALUES(?,?,?,?)',
                            (unit['lesson_id'],topics[topic_key],unit['title'],now))
                con.execute('INSERT OR IGNORE INTO plan_units VALUES(?,?,?)',
                            (plan['id'],unit['lesson_id'],json.dumps(unit,ensure_ascii=False)))
                material_id = 'source_'+unit['lesson_id']
                page = unit['pages'][0] if unit['pages'] else 31
                con.execute('INSERT OR IGNORE INTO materials(material_id,lesson_id,title,url,position,created_at) VALUES(?,?,?,?,?,?)',
                            (material_id,unit['lesson_id'],'Edital oficial · Anexo II · página '+str(page),
                             unit['source_url']+'#page='+str(page),0,now))
        con.commit()
        count = con.execute('SELECT count(*) FROM plan_units WHERE plan_id=?',(plan['id'],)).fetchone()[0]
        assert count==plan['coverage']['lessons']
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
        print(json.dumps(dict(plan=plan['id'],lessons=count,added=con.execute('SELECT count(*) FROM lessons').fetchone()[0]-before,
                              backup=str(backup)),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--install',type=Path,required=True,help='Existing study database; makes an SQLite backup before additive import.')
    args=parser.parse_args()
    install(args.install)
