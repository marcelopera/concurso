"""SQLite queries for plans; transactions are owned by application services."""


def lesson_metadata(con, parameters):
    return con.execute("SELECT metadata_json FROM plan_units WHERE lesson_id=?", parameters).fetchone()


def latest_config(con):
    return con.execute("SELECT config_json FROM study_plans ORDER BY created_at DESC,rowid DESC LIMIT 1").fetchone()


def question_counts(con):
    return con.execute("SELECT lesson_id,count(*) FROM lesson_questions GROUP BY lesson_id").fetchall()


def units(con, parameters):
    return con.execute(
        """
        SELECT u.metadata_json, l.lesson_id, l.title, l.completed_at, t.title AS topic_title, s.name AS subject_name
        FROM plan_units u JOIN lessons l USING(lesson_id) JOIN topics t USING(topic_id) JOIN subjects s
        USING(subject_id) WHERE u.plan_id=?
        """,
        parameters,
    ).fetchall()


def activity_progress(con, parameters):
    return con.execute("SELECT * FROM plan_activity_progress WHERE plan_id=?", parameters).fetchall()


def latest_plan(con):
    return con.execute(
        "SELECT plan_id,config_json FROM study_plans ORDER BY created_at DESC,rowid DESC LIMIT 1"
    ).fetchone()


def save_activity(con, parameters):
    return con.execute(
        """
        INSERT INTO plan_activity_progress(plan_id,activity_id,completed_at,note) VALUES(?,?,?,?) ON
        CONFLICT(plan_id,activity_id) DO UPDATE SET completed_at=excluded.completed_at,note=excluded.note
        """,
        parameters,
    )


def enable_foreign_keys(con):
    return con.execute("PRAGMA foreign_keys=ON")


def begin_write(con):
    return con.execute("BEGIN IMMEDIATE")


def lesson_count(con):
    return con.execute("SELECT count(*) FROM lessons").fetchone()


def plan_config(con, parameters):
    return con.execute("SELECT config_json FROM study_plans WHERE plan_id=?", parameters).fetchone()


def insert_plan(con, parameters):
    return con.execute("INSERT OR IGNORE INTO study_plans VALUES(?,?,?)", parameters)


def insert_subject(con, parameters):
    return con.execute("INSERT OR IGNORE INTO subjects VALUES(?,?,?)", parameters)


def subject_by_name(con, parameters):
    return con.execute("SELECT subject_id FROM subjects WHERE name=? COLLATE NOCASE", parameters).fetchone()


def insert_topic(con, parameters):
    return con.execute("INSERT OR IGNORE INTO topics VALUES(?,?,?,?,?)", parameters)


def topic_by_title(con, parameters):
    return con.execute("SELECT topic_id FROM topics WHERE subject_id=? AND title=?", parameters).fetchone()


def other_owner(con, parameters):
    return con.execute("SELECT plan_id FROM plan_units WHERE lesson_id=? AND plan_id<>?", parameters).fetchone()


def lesson_topic(con, parameters):
    return con.execute("SELECT topic_id FROM lessons WHERE lesson_id=?", parameters).fetchone()


def unit_metadata(con, parameters):
    return con.execute("SELECT metadata_json FROM plan_units WHERE plan_id=? AND lesson_id=?", parameters).fetchone()


def insert_lesson(con, parameters):
    return con.execute("INSERT OR IGNORE INTO lessons(lesson_id,topic_id,title,created_at) VALUES(?,?,?,?)", parameters)


def insert_unit(con, parameters):
    return con.execute("INSERT OR IGNORE INTO plan_units VALUES(?,?,?)", parameters)


def insert_material(con, parameters):
    return con.execute(
        "INSERT OR IGNORE INTO materials(material_id,lesson_id,title,url,position,created_at) VALUES(?,?,?,?,?,?)",
        parameters,
    )


def unit_count(con, parameters):
    return con.execute("SELECT count(*) FROM plan_units WHERE plan_id=?", parameters).fetchone()


def foreign_key_errors(con):
    return con.execute("PRAGMA foreign_key_check").fetchall()
