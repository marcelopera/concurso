CREATE TABLE IF NOT EXISTS subjects (
        subject_id TEXT PRIMARY KEY,
        name TEXT NOT NULL COLLATE NOCASE UNIQUE,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS topics (
        topic_id TEXT PRIMARY KEY,
        subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        UNIQUE(subject_id, title)
    );
    CREATE TABLE IF NOT EXISTS lessons (
        lesson_id TEXT PRIMARY KEY,
        topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        completed_at TEXT,
        reference_scene TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS lesson_questions (
        lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        occurrence_id TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(lesson_id, occurrence_id)
    );
    CREATE TABLE IF NOT EXISTS materials (
        material_id TEXT PRIMARY KEY,
        lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        url TEXT,
        document_id TEXT,
        position INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        CHECK ((url IS NOT NULL AND document_id IS NULL) OR
               (url IS NULL AND document_id IS NOT NULL))
    );
    CREATE TABLE IF NOT EXISTS study_sessions (
        session_id TEXT PRIMARY KEY,
        lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        status TEXT NOT NULL CHECK(status IN ('active','completed')),
        current_step INTEGER NOT NULL DEFAULT 0 CHECK(current_step BETWEEN 0 AND 5),
        deadline_at TEXT,
        paused_remaining INTEGER,
        payload TEXT NOT NULL DEFAULT '{}',
        started_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT
    );
    CREATE INDEX IF NOT EXISTS ix_sessions_status ON study_sessions(status, updated_at);
    CREATE TABLE IF NOT EXISTS attempts (
        attempt_id TEXT PRIMARY KEY,
        session_id TEXT REFERENCES study_sessions(session_id) ON DELETE SET NULL,
        stage TEXT NOT NULL,
        occurrence_id TEXT NOT NULL,
        answer TEXT NOT NULL,
        help_used INTEGER NOT NULL DEFAULT 0,
        reference_snapshot TEXT NOT NULL,
        correct INTEGER,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_attempts_created ON attempts(created_at DESC);
    CREATE TABLE IF NOT EXISTS cards (
        card_id TEXT PRIMARY KEY,
        topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
        source_session_id TEXT REFERENCES study_sessions(session_id) ON DELETE SET NULL,
        front TEXT NOT NULL,
        back TEXT NOT NULL,
        difficulty TEXT NOT NULL DEFAULT '',
        interval_days INTEGER NOT NULL DEFAULT 1 CHECK(interval_days IN (1,3,7)),
        due_date TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_cards_due ON cards(active, due_date);
    CREATE TABLE IF NOT EXISTS card_reviews (
        review_id TEXT PRIMARY KEY,
        card_id TEXT NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
        rating TEXT NOT NULL CHECK(rating IN ('errei','dificil','facil')),
        interval_before INTEGER NOT NULL,
        interval_after INTEGER NOT NULL,
        due_after TEXT NOT NULL,
        reviewed_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS lesson_difficulties (
        difficulty_id TEXT PRIMARY KEY,
        lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
        session_id TEXT NOT NULL REFERENCES study_sessions(session_id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL
    );


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


CREATE TABLE IF NOT EXISTS question_mapping_runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    report_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lesson_question_mappings (
    lesson_id TEXT NOT NULL,
    occurrence_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence TEXT NOT NULL,
    method TEXT NOT NULL,
    score REAL NOT NULL,
    evidence_json TEXT NOT NULL,
    syllabus_excerpt TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL REFERENCES question_mapping_runs(run_id),
    PRIMARY KEY(lesson_id, occurrence_id),
    FOREIGN KEY(lesson_id, occurrence_id) REFERENCES lesson_questions(lesson_id, occurrence_id) ON DELETE CASCADE
);
