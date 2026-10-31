"""SQLite queries for lessons; transactions are owned by application services."""


def lesson(con, parameters):
    return con.execute(
        """
        SELECT l.*, t.title AS topic_title, s.name AS subject_name FROM lessons l JOIN topics t USING(topic_id) JOIN
        subjects s USING(subject_id) WHERE lesson_id=?
        """,
        parameters,
    ).fetchone()


def question_ids(con, parameters):
    return con.execute(
        "SELECT occurrence_id FROM lesson_questions WHERE lesson_id=? ORDER BY position, occurrence_id", parameters
    ).fetchall()


def materials(con, parameters):
    return con.execute("SELECT * FROM materials WHERE lesson_id=? ORDER BY position, created_at", parameters).fetchall()


def subjects(con):
    return con.execute("SELECT * FROM subjects ORDER BY name").fetchall()


def topics(con, parameters):
    return con.execute("SELECT * FROM topics WHERE subject_id=? ORDER BY position,title", parameters).fetchall()


def lessons(con, parameters):
    return con.execute(
        "SELECT lesson_id AS id,title,completed_at,created_at FROM lessons WHERE topic_id=? ORDER BY created_at, lesson_id",
        parameters,
    ).fetchall()


def active_sessions(con):
    return con.execute(
        """
        SELECT ss.*,l.title AS lesson_title,l.topic_id,t.title AS topic_title,s.name AS subject_name FROM
        study_sessions ss JOIN lessons l USING(lesson_id) JOIN topics t USING(topic_id) JOIN subjects s
        USING(subject_id) WHERE ss.status='active' ORDER BY ss.updated_at DESC, ss.session_id DESC
        """
    ).fetchall()


def document(con, parameters):
    return con.execute("SELECT arquivo_local FROM documentos WHERE documento_id=?", parameters).fetchone()


def lesson_exists(con, parameters):
    return con.execute("SELECT 1 FROM lessons WHERE lesson_id=?", parameters).fetchone()


def next_material_position(con, parameters):
    return con.execute("SELECT coalesce(max(position),-1)+1 FROM materials WHERE lesson_id=?", parameters).fetchone()


def insert_material(con, parameters):
    return con.execute(
        "INSERT INTO materials(material_id,lesson_id,title,url,document_id,position,created_at) VALUES(?,?,?,?,?,?,?)",
        parameters,
    )


def subject_by_name(con, parameters):
    return con.execute("SELECT subject_id FROM subjects WHERE name=? COLLATE NOCASE", parameters).fetchone()


def insert_subject(con, parameters):
    return con.execute("INSERT INTO subjects(subject_id,name,created_at) VALUES(?,?,?)", parameters)


def next_topic_position(con, parameters):
    return con.execute("SELECT coalesce(max(position),-1)+1 FROM topics WHERE subject_id=?", parameters).fetchone()


def insert_topic(con, parameters):
    return con.execute(
        "INSERT INTO topics(topic_id,subject_id,title,position,created_at) VALUES(?,?,?,?,?)", parameters
    )


def topic_exists(con, parameters):
    return con.execute("SELECT 1 FROM topics WHERE topic_id=?", parameters).fetchone()


def insert_lesson(con, parameters):
    return con.execute("INSERT INTO lessons(lesson_id,topic_id,title,created_at) VALUES(?,?,?,?)", parameters)


def update_title(con, parameters):
    return con.execute("UPDATE lessons SET title=? WHERE lesson_id=?", parameters)


def update_reference(con, parameters):
    return con.execute("UPDATE lessons SET title=?,reference_scene=? WHERE lesson_id=?", parameters)


def question_ids_record(con, parameters):
    return con.execute("SELECT occurrence_id FROM lesson_questions WHERE lesson_id=?", parameters).fetchall()


def remove_questions(con, parameters):
    return con.executemany("DELETE FROM lesson_questions WHERE lesson_id=? AND occurrence_id=?", parameters)


def save_questions(con, parameters):
    return con.executemany(
        """
        INSERT INTO lesson_questions(lesson_id,occurrence_id,position) VALUES(?,?,?) ON
        CONFLICT(lesson_id,occurrence_id) DO UPDATE SET position=excluded.position
        """,
        parameters,
    )


def delete_material(con, parameters):
    return con.execute("DELETE FROM materials WHERE material_id=?", parameters)
