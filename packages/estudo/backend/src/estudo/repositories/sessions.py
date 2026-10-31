"""SQLite queries for sessions; transactions are owned by application services."""


def session(con, parameters):
    return con.execute("SELECT * FROM study_sessions WHERE session_id=?", parameters).fetchone()


def linked_question(con, parameters):
    return con.execute("SELECT 1 FROM lesson_questions WHERE lesson_id=? AND occurrence_id=?", parameters).fetchone()


def insert_attempt(con, parameters):
    return con.execute(
        """
        INSERT INTO
        attempts(attempt_id,session_id,stage,occurrence_id,answer,help_used,reference_snapshot,correct,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        parameters,
    )


def begin_write(con):
    return con.execute("BEGIN IMMEDIATE")


def lesson_topic(con, parameters):
    return con.execute("SELECT topic_id FROM lessons WHERE lesson_id=?", parameters).fetchone()


def insert_card(con, parameters):
    return con.execute(
        """
        INSERT INTO
        cards(card_id,topic_id,source_session_id,front,back,difficulty,interval_days,due_date,created_at)
        VALUES(?,?,?,?,?,?,1,?,?)
        """,
        parameters,
    )


def insert_difficulty(con, parameters):
    return con.execute(
        "INSERT INTO lesson_difficulties(difficulty_id,lesson_id,session_id,text,created_at) VALUES(?,?,?,?,?)",
        parameters,
    )


def complete_lesson(con, parameters):
    return con.execute("UPDATE lessons SET completed_at=coalesce(completed_at,?) WHERE lesson_id=?", parameters)


def complete_session(con, parameters):
    return con.execute(
        """
        UPDATE study_sessions SET
        status='completed',completed_at=?,updated_at=?,current_step=5,deadline_at=NULL,paused_remaining=0 WHERE
        session_id=?
        """,
        parameters,
    )


def active_card(con, parameters):
    return con.execute("SELECT * FROM cards WHERE card_id=? AND active=1", parameters).fetchone()


def update_card(con, parameters):
    return con.execute("UPDATE cards SET interval_days=?,due_date=? WHERE card_id=?", parameters)


def insert_review(con, parameters):
    return con.execute(
        """
        INSERT INTO card_reviews(review_id,card_id,rating,interval_before,interval_after,due_after,reviewed_at)
        VALUES(?,?,?,?,?,?,?)
        """,
        parameters,
    )


def card(con, parameters):
    return con.execute("SELECT * FROM cards WHERE card_id=?", parameters).fetchone()


def due_cards(con, parameters):
    return con.execute(
        """
        SELECT c.*,t.title AS topic_title,s.name AS subject_name FROM cards c JOIN topics t USING(topic_id) JOIN
        subjects s USING(subject_id) WHERE c.active=1 AND c.due_date<=? ORDER BY c.due_date,c.created_at LIMIT 80
        """,
        parameters,
    ).fetchall()


def attempt_history(con):
    return con.execute(
        """
        SELECT attempt_id,stage,occurrence_id,answer,help_used,reference_snapshot,correct,created_at FROM attempts
        WHERE session_id IS NULL ORDER BY created_at DESC LIMIT 100
        """
    ).fetchall()


def lesson_exists(con, parameters):
    return con.execute("SELECT 1 FROM lessons WHERE lesson_id=?", parameters).fetchone()


def active_for_lesson(con, parameters):
    return con.execute(
        "SELECT * FROM study_sessions WHERE status='active' AND lesson_id=? ORDER BY updated_at DESC LIMIT 1",
        parameters,
    ).fetchone()


def previous_payload(con, parameters):
    return con.execute(
        """
        SELECT payload FROM study_sessions WHERE lesson_id=? AND status='completed' ORDER BY completed_at DESC,
        rowid DESC LIMIT 1
        """,
        parameters,
    ).fetchone()


def insert_session(con, parameters):
    return con.execute(
        """
        INSERT INTO
        study_sessions(session_id,lesson_id,status,current_step,deadline_at,payload,started_at,updated_at)
        VALUES(?,?,'active',0,?,?,?,?)
        """,
        parameters,
    )


def active_session(con, parameters):
    return con.execute("SELECT * FROM study_sessions WHERE session_id=? AND status='active'", parameters).fetchone()


def change_step(con, parameters):
    return con.execute(
        "UPDATE study_sessions SET current_step=?,deadline_at=?,paused_remaining=NULL,updated_at=? WHERE session_id=?",
        parameters,
    )


def pause(con, parameters):
    return con.execute(
        "UPDATE study_sessions SET deadline_at=NULL,paused_remaining=?,updated_at=? WHERE session_id=?", parameters
    )


def resume(con, parameters):
    return con.execute(
        "UPDATE study_sessions SET deadline_at=?,paused_remaining=NULL,updated_at=? WHERE session_id=?", parameters
    )


def save_state(con, parameters):
    return con.execute(
        "UPDATE study_sessions SET payload=?,updated_at=? WHERE session_id=? AND status='active'", parameters
    )
