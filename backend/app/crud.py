"""
All database operations for Cognify.
Uses raw SQL via SQLAlchemy text() — simple and fast for MVP.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


# ── Users ──────────────────────────────────────────────────────────────────────

def create_user(db: Session, name: str, email: str, password_hash: str) -> dict:
    row = db.execute(
        text("""
            INSERT INTO users (name, email, password_hash)
            VALUES (:name, :email, :pw)
            RETURNING id, name, email, created_at
        """),
        {"name": name, "email": email, "pw": password_hash},
    ).fetchone()
    db.commit()
    return dict(row._mapping)


def get_user_by_email(db: Session, email: str) -> dict | None:
    row = db.execute(
        text("SELECT id, name, email, password_hash FROM users WHERE email = :e"),
        {"e": email},
    ).fetchone()
    return dict(row._mapping) if row else None


def get_user_by_id(db: Session, user_id: int) -> dict | None:
    row = db.execute(
        text("SELECT id, name, email FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).fetchone()
    return dict(row._mapping) if row else None


# ── Concepts ───────────────────────────────────────────────────────────────────

def get_or_create_concept(
    db: Session, name: str, display_name: str, topic: str, subtopic: str = ""
) -> int:
    """Return concept id, inserting if it doesn't exist."""
    row = db.execute(
        text("SELECT id FROM concepts WHERE name = :n"),
        {"n": name},
    ).fetchone()
    if row:
        return row[0]

    row = db.execute(
        text("""
            INSERT INTO concepts (name, display_name, topic, subtopic)
            VALUES (:n, :dn, :t, :st)
            RETURNING id
        """),
        {"n": name, "dn": display_name, "t": topic, "st": subtopic},
    ).fetchone()
    db.commit()
    return row[0]


def get_concept_id(db: Session, concept_name: str) -> int | None:
    row = db.execute(
        text("SELECT id FROM concepts WHERE name = :n"),
        {"n": concept_name},
    ).fetchone()
    return row[0] if row else None


# ── Skill Vector ───────────────────────────────────────────────────────────────

def get_skill(db: Session, user_id: int, concept_id: int) -> float:
    row = db.execute(
        text("SELECT skill FROM user_skill WHERE user_id=:u AND concept_id=:c"),
        {"u": user_id, "c": concept_id},
    ).fetchone()
    return float(row[0]) if row else 1000.0


def upsert_skill(db: Session, user_id: int, concept_id: int, new_skill: float) -> None:
    db.execute(
        text("""
            INSERT INTO user_skill (user_id, concept_id, skill, updated_at)
            VALUES (:u, :c, :s, NOW())
            ON CONFLICT (user_id, concept_id)
            DO UPDATE SET skill = :s, updated_at = NOW()
        """),
        {"u": user_id, "c": concept_id, "s": new_skill},
    )
    db.commit()


def get_all_skills(db: Session, user_id: int) -> dict[str, float]:
    """Return {concept_name: skill} for all concepts a user has practiced."""
    rows = db.execute(
        text("""
            SELECT c.name, us.skill
            FROM user_skill us
            JOIN concepts c ON c.id = us.concept_id
            WHERE us.user_id = :u
        """),
        {"u": user_id},
    ).fetchall()
    return {r[0]: float(r[1]) for r in rows}


# ── Questions ──────────────────────────────────────────────────────────────────

def insert_question(
    db: Session,
    text_: str,
    subtopics: list[str],
    difficulty: int,
    source_url: str,
    text_hash: str,
    embedding_id: str = "",
    question_type: str = "numerical",
    options: dict | None = None,
    correct_option: str | None = None,
    correct_answer: str | None = None,
) -> int:
    """Insert a question; return its Postgres id. Skips if hash exists."""
    existing = db.execute(
        text("SELECT id FROM questions WHERE text_hash = :h"),
        {"h": text_hash},
    ).fetchone()
    if existing:
        return existing[0]

    import json
    options_str = json.dumps(options) if options else None
    row = db.execute(
        text("""
            INSERT INTO questions
              (text, question_type, options, correct_option, correct_answer,
               subtopics, difficulty, source_url, text_hash, embedding_id)
            VALUES (:t, :qtype, :opts, :copt, :cans,
                    CAST(:st AS jsonb), :d, :url, :h, :eid)
            RETURNING id
        """),
        {
            "t": text_,
            "qtype": question_type,
            "opts": options_str,
            "copt": correct_option,
            "cans": correct_answer,
            "st": json.dumps(subtopics),
            "d": difficulty,
            "url": source_url,
            "h": text_hash,
            "eid": embedding_id,
        },
    ).fetchone()
    db.commit()
    return row[0]


def get_question_by_id(db: Session, question_id: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT id, text, question_type, options, correct_option, correct_answer,
                   subtopics, difficulty, source_url
            FROM questions WHERE id = :qid
        """),
        {"qid": question_id},
    ).fetchone()
    return dict(row._mapping) if row else None


def get_questions_by_subtopic(
    db: Session, subtopic: str, limit: int = 10
) -> list[dict]:
    """Fallback: fetch questions from DB when Pinecone returns nothing."""
    rows = db.execute(
        text("""
            SELECT id, text, subtopics, difficulty, source_url
            FROM questions
            WHERE subtopics::text ILIKE :s
            ORDER BY RANDOM()
            LIMIT :lim
        """),
        {"s": f"%{subtopic}%", "lim": limit},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def get_adaptive_questions(
    db: Session,
    subtopic: str,
    exclude_ids: list[int],
    diff_min: int,
    diff_max: int,
    limit: int = 10,
) -> list[dict]:
    """
    Adaptive fetch: filter by difficulty band, exclude already-seen questions,
    randomise order so the same question never repeats in a row.
    Falls back to any difficulty if the band returns nothing.
    """
    import json as _json

    def _fetch(d_min: int, d_max: int) -> list[dict]:
        exclude_clause = ""
        params: dict = {"s": f"%{subtopic}%", "d_min": d_min, "d_max": d_max, "lim": limit}
        if exclude_ids:
            # Build a safe exclusion list
            placeholders = ", ".join(f":ex{i}" for i in range(len(exclude_ids)))
            exclude_clause = f"AND id NOT IN ({placeholders})"
            for i, eid in enumerate(exclude_ids):
                params[f"ex{i}"] = eid
        rows = db.execute(
            text(f"""
                SELECT id, text, subtopics, difficulty, source_url
                FROM questions
                WHERE subtopics::text ILIKE :s
                  AND difficulty BETWEEN :d_min AND :d_max
                  {exclude_clause}
                ORDER BY RANDOM()
                LIMIT :lim
            """),
            params,
        ).fetchall()
        return [dict(r._mapping) for r in rows]

    results = _fetch(diff_min, diff_max)
    # If the difficulty band is empty, widen to any difficulty
    if not results:
        results = _fetch(1, 5)
    return results


def count_questions_by_subtopic(db: Session, subtopic: str) -> int:
    """Count how many questions we have for a subtopic (for low-stock detection)."""
    row = db.execute(
        text("SELECT COUNT(*) FROM questions WHERE subtopics::text ILIKE :s"),
        {"s": f"%{subtopic}%"},
    ).fetchone()
    return int(row[0]) if row else 0


def get_seen_question_ids(db: Session, user_id: int, subtopic: str) -> list[int]:
    """Return IDs of questions this user has already attempted for a given subtopic."""
    rows = db.execute(
        text("""
            SELECT DISTINCT a.question_id
            FROM attempts a
            JOIN questions q ON q.id = a.question_id
            WHERE a.user_id = :u
              AND q.subtopics::text ILIKE :s
        """),
        {"u": user_id, "s": f"%{subtopic}%"},
    ).fetchall()
    return [r[0] for r in rows]


# ── Attempts ───────────────────────────────────────────────────────────────────

def record_attempt(
    db: Session,
    user_id: int,
    question_id: int,
    is_correct: bool,
    time_taken: float,
    retries: int,
    hint_used: bool,
    cms: float,
) -> dict:
    row = db.execute(
        text("""
            INSERT INTO attempts
              (user_id, question_id, is_correct, time_taken, retries, hint_used, cms)
            VALUES (:u, :q, :ic, :tt, :r, :hu, :cms)
            RETURNING id, created_at
        """),
        {
            "u": user_id, "q": question_id, "ic": is_correct,
            "tt": time_taken, "r": retries, "hu": hint_used,
            "cms": cms,
        },
    ).fetchone()
    db.commit()
    return dict(row._mapping)


def get_recent_attempts(db: Session, user_id: int, n: int = 10) -> list[dict]:
    import json as _json
    rows = db.execute(
        text("""
            SELECT a.id, q.text, q.subtopics::text as subtopics_raw,
                   a.is_correct, a.time_taken, a.cms, a.created_at
            FROM attempts a
            JOIN questions q ON q.id = a.question_id
            WHERE a.user_id = :u
            ORDER BY a.created_at DESC
            LIMIT :n
        """),
        {"u": user_id, "n": n},
    ).fetchall()
    results = []
    for r in rows:
        row = dict(r._mapping)
        try:
            subtopics = _json.loads(row.pop("subtopics_raw", "[]"))
            row["concept"] = subtopics[0] if subtopics else "general"
        except Exception:
            row["concept"] = "general"
        results.append(row)
    return results


def get_incorrect_streak(db: Session, user_id: int, question_id: int) -> int:
    """Count consecutive incorrect attempts for a specific question."""
    rows = db.execute(
        text("""
            SELECT is_correct FROM attempts
            WHERE user_id = :u AND question_id = :q
            ORDER BY created_at DESC
            LIMIT 5
        """),
        {"u": user_id, "q": question_id},
    ).fetchall()
    streak = 0
    for r in rows:
        if not r[0]:
            streak += 1
        else:
            break
    return streak


def get_avg_cms(db: Session, user_id: int, n: int = 10) -> float:
    row = db.execute(
        text("""
            SELECT AVG(cms) FROM (
                SELECT cms FROM attempts
                WHERE user_id = :u AND cms IS NOT NULL
                ORDER BY created_at DESC
                LIMIT :n
            ) sub
        """),
        {"u": user_id, "n": n},
    ).fetchone()
    val = row[0] if row and row[0] is not None else 0.5
    return round(float(val), 4)
