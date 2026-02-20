-- Cognify: JEE Maths Adaptive Learning
-- Initial schema — run once: psql -d cognify -f migrations/001_init.sql

CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    name        TEXT        NOT NULL,
    email       TEXT        UNIQUE NOT NULL,
    password_hash TEXT      NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concepts (
    id          SERIAL PRIMARY KEY,
    name        TEXT        UNIQUE NOT NULL,   -- e.g. "integration_by_parts"
    display_name TEXT       NOT NULL,          -- e.g. "Integration by Parts"
    topic       TEXT        NOT NULL,          -- e.g. "Calculus"
    subtopic    TEXT                           -- e.g. "Integration"
);

-- Directed edges: concept_id depends on prereq_id
CREATE TABLE IF NOT EXISTS concept_graph (
    concept_id  INT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    prereq_id   INT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (concept_id, prereq_id)
);

CREATE TABLE IF NOT EXISTS user_skill (
    user_id     INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concept_id  INT  NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    skill       FLOAT NOT NULL DEFAULT 1000.0,
    updated_at  TIMESTAMPTZ   DEFAULT NOW(),
    PRIMARY KEY (user_id, concept_id)
);

CREATE TABLE IF NOT EXISTS questions (
    id              SERIAL PRIMARY KEY,
    text            TEXT        NOT NULL,
    subtopics       JSONB       NOT NULL DEFAULT '[]',  -- ["integration_by_parts"]
    difficulty      INT         NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    source_url      TEXT,
    embedding_id    TEXT,       -- Pinecone vector ID
    text_hash       TEXT UNIQUE NOT NULL,  -- SHA256 for deduplication
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attempts (
    id              SERIAL PRIMARY KEY,
    user_id         INT     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id     INT     NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    is_correct      BOOLEAN NOT NULL,
    time_taken      FLOAT   NOT NULL,   -- seconds
    retries         INT     NOT NULL DEFAULT 0,
    hint_used       BOOLEAN NOT NULL DEFAULT FALSE,
    confidence      INT     NOT NULL CHECK (confidence BETWEEN 1 AND 5),
    cms             FLOAT,              -- computed after insert
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast skill lookups
CREATE INDEX IF NOT EXISTS idx_user_skill_lookup ON user_skill(user_id, concept_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user     ON attempts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_questions_hash    ON questions(text_hash);
