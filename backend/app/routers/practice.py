"""
Practice router — core session management.
  POST /practice/start   → select topic, retrieve learner state, serve questions
  POST /practice/answer  → record attempt, compute CMS, update skill, maybe remediate
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud
from app.db import get_db
from app.services.cms import compute_cms
from app.services.concept_graph import get_all_concepts, load_graph
from app.services.elo import get_or_init_skill, persist_skill, update_skill
from app.services.gemini_client import get_embedding, check_answer
from app.services.ingestion import ingest_topic
from app.services.pinecone_client import query_questions
from app.services.remediation import should_remediate, trigger_remediation
from app.services.supermemory import get_learner_state, write_session_summary
import threading

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class PracticeStartRequest(BaseModel):
    user_id: int
    topic: str          # e.g. "integration_by_parts" or "adaptive"
    n: int = 5          # number of questions to serve


# ── ELO → Difficulty band ──────────────────────────────────────────────────────

# Pure weak-focus: ELO controls how hard the questions are.
# The weaker you are, the easier the questions — build foundation first.
_ELO_BANDS: list[tuple[float, int, int]] = [
    # (ELO upper bound,  diff_min, diff_max)
    (850,  1, 2),   # critical — remediation, very easy
    (950,  2, 3),   # weak — consolidation
    (1050, 3, 4),   # normal
    (1150, 4, 5),   # strong
    (9999, 5, 5),   # mastery
]

def _elo_to_difficulty(elo: float) -> tuple[int, int]:
    for upper, d_min, d_max in _ELO_BANDS:
        if elo < upper:
            return d_min, d_max
    return 5, 5


# Low-stock threshold — trigger background ingest when unseen count drops below this
_LOW_STOCK = 3


class AnswerRequest(BaseModel):
    user_id: int
    question_id: int
    user_answer: str        # student's typed answer
    time_taken: float       # seconds
    retries: int = 0
    hint_used: bool = False
    confidence: int = 3     # 1–5, optional (defaults to middle)


# ── Helpers ────────────────────────────────────────────────────────────────────

_QUESTION_STARTERS = (
    "find", "evaluate", "calculate", "compute", "prove", "show", "determine",
    "if ", "let ", "for ", "given", "solve", "integrate", "differentiate",
    "a ", "the ", "which", "what", "how", "when", "using", "without",
)

def _is_valid_question(text: str) -> bool:
    """Return True if text looks like a real JEE math question (not scraped article text)."""
    t = text.strip()
    if not t or len(t) < 10:
        return False
    # Reject obviously long article text (real questions are usually < 350 chars)
    if len(t) > 400:
        return False
    t_lower = t.lower()
    # Accept if it ends with "?" or starts with a known question word
    if t.endswith("?"):
        return True
    if any(t_lower.startswith(s) for s in _QUESTION_STARTERS):
        return True
    # Accept if it contains LaTeX-style math markers
    if any(marker in t for marker in ["∫", "∑", "∏", "√", "²", "³", "^", "dx", "dy"]):
        return True
    return False


def _ensure_concept(db: Session, concept_name: str) -> int:
    """Get or create the concept in DB, using graph metadata for display info."""
    graph = load_graph()
    node = graph.get(concept_name, {})
    return crud.get_or_create_concept(
        db,
        name=concept_name,
        display_name=node.get("display_name", concept_name.replace("_", " ").title()),
        topic=node.get("topic", "General"),
        subtopic=node.get("subtopic", ""),
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/start")
def start_session(body: PracticeStartRequest, db: Session = Depends(get_db)):
    """
    Full flow:
    1. Get learner state from Supermemory
    2. Get skill vector from Postgres
    3. Get concept embedding → query Pinecone for matching questions
    4. If not enough questions → ingest from web
    5. Return question set
    """
    # Validate concept
    all_concepts = get_all_concepts()
    if body.topic not in all_concepts:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown topic '{body.topic}'. Valid topics: {all_concepts[:10]}..."
        )

    # 1. Learner state from Supermemory
    learner_state = get_learner_state(body.user_id)

    # 2. Skill from Postgres — determines difficulty band
    concept_id = _ensure_concept(db, body.topic)
    skill = get_or_init_skill(db, body.user_id, concept_id)
    diff_min, diff_max = _elo_to_difficulty(skill)

    # 3. IDs the user has already seen for this topic → exclude from selection
    seen_ids_list = crud.get_seen_question_ids(db, body.user_id, body.topic)
    seen_ids: set[int] = set(seen_ids_list)

    # 4. Low-stock check → fire background ingest so future sessions have fresh Qs
    total_in_db = crud.count_questions_by_subtopic(db, body.topic)
    unseen_count = total_in_db - len(seen_ids)
    if unseen_count < _LOW_STOCK:
        def _bg_ingest(topic: str) -> None:
            try:
                ingest_topic(topic, n=10)
            except Exception as exc:
                print(f"[BG Ingest] {topic}: {exc}")
        threading.Thread(target=_bg_ingest, args=(body.topic,), daemon=True).start()

    # 5. Adaptive DB fetch — difficulty-banded, unseen-first, randomised
    db_questions = crud.get_adaptive_questions(
        db,
        subtopic=body.topic,
        exclude_ids=seen_ids_list,
        diff_min=diff_min,
        diff_max=diff_max,
        limit=body.n,
    )

    # If not enough unseen Qs, top up with already-seen ones (still randomised)
    if len(db_questions) < body.n:
        extra = crud.get_adaptive_questions(
            db,
            subtopic=body.topic,
            exclude_ids=[q["id"] for q in db_questions],  # avoid duplicates in this batch
            diff_min=diff_min,
            diff_max=diff_max,
            limit=body.n - len(db_questions),
        )
        db_questions.extend(extra)

    questions = [
        {
            "id": q["id"],
            "text": q["text"],
            "subtopics": q["subtopics"] if isinstance(q["subtopics"], list) else [],
            "difficulty": int(q["difficulty"]),
        }
        for q in db_questions
    ]
    result_ids = {q["id"] for q in questions}

    # 6. Still short? Pull from Pinecone (semantic similarity)
    if len(questions) < body.n:
        try:
            query_emb = get_embedding(body.topic.replace("_", " "))
            pinecone_hits = query_questions(
                subtopic=body.topic,
                query_embedding=query_emb,
                n=(body.n - len(questions)) * 2,
            )
            for ph in (pinecone_hits or []):
                db_id = crud.insert_question(
                    db,
                    text_=ph["text"],
                    subtopics=ph.get("subtopics", [body.topic]),
                    difficulty=int(ph.get("difficulty", 3)),
                    source_url=ph.get("source_url", ""),
                    text_hash=ph["text_hash"],
                    embedding_id=ph.get("question_id", ""),
                )
                if db_id not in result_ids and _is_valid_question(ph["text"]):
                    questions.append({
                        "id": db_id,
                        "text": ph["text"],
                        "subtopics": ph.get("subtopics", [body.topic]),
                        "difficulty": int(ph.get("difficulty", 3)),
                    })
                    result_ids.add(db_id)
                if len(questions) >= body.n:
                    break
        except Exception as e:
            print(f"[Practice] Pinecone error: {e}")

    if not questions:
        raise HTTPException(
            status_code=404,
            detail=f"No questions found for topic '{body.topic}'. Try another topic."
        )

    return {
        "user_id": body.user_id,
        "topic": body.topic,
        "skill": skill,
        "difficulty_band": [diff_min, diff_max],
        "learner_state": learner_state,
        "questions": questions[:body.n],
        "questions_count": min(len(questions), body.n),
    }


@router.post("/answer")
def submit_answer(body: AnswerRequest, db: Session = Depends(get_db)):
    """
    Full flow:
    1. Validate question + confidence
    2. Compute CMS
    3. ELO skill update in Postgres
    4. Check concept graph for weak prereqs
    5. Write behavior summary to Supermemory
    6. Trigger remediation if needed
    7. Return updated skill + next action
    """
    # Validate confidence range
    if not 1 <= body.confidence <= 5:
        raise HTTPException(status_code=400, detail="confidence must be 1–5")

    # Verify question exists
    question = crud.get_question_by_id(db, body.question_id)
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {body.question_id} not found")

    # Auto-check the student's answer using Gemini
    check = check_answer(question.get("text", ""), body.user_answer)
    is_correct = check.get("is_correct", False)
    correct_answer = check.get("correct_answer", "")
    explanation = check.get("explanation", "")

    # Determine concept from question's first subtopic
    subtopics = question.get("subtopics") or []
    if isinstance(subtopics, str):
        import json
        subtopics = json.loads(subtopics)
    concept_name = subtopics[0] if subtopics else "unknown"

    concept_id = _ensure_concept(db, concept_name)

    # 1. CMS
    cms = compute_cms(
        is_correct=is_correct,
        time_taken=body.time_taken,
        retries=body.retries,
        hint_used=body.hint_used,
        confidence=body.confidence,
    )

    # 2. Record attempt
    crud.record_attempt(
        db,
        user_id=body.user_id,
        question_id=body.question_id,
        is_correct=is_correct,
        time_taken=body.time_taken,
        retries=body.retries,
        hint_used=body.hint_used,
        confidence=body.confidence,
        cms=cms,
    )

    # 3. ELO skill update
    difficulty = question.get("difficulty", 3)
    old_skill = get_or_init_skill(db, body.user_id, concept_id)
    new_skill = update_skill(old_skill, difficulty, cms)
    persist_skill(db, body.user_id, concept_id, new_skill)

    # 4. Concept graph prereq check
    skill_map = crud.get_all_skills(db, body.user_id)
    skill_map[concept_name] = new_skill

    # 5. Supermemory — write behavior note
    status = "correct" if is_correct else "incorrect"
    summary = (
        f"User {body.user_id} attempted '{concept_name}' (difficulty {difficulty}). "
        f"Result: {status}. CMS: {cms:.3f}. Skill updated: {old_skill:.0f} → {new_skill:.0f}."
    )
    write_session_summary(
        body.user_id,
        summary,
        metadata={"concept": concept_name, "cms": str(cms), "is_correct": str(is_correct)},
    )

    # 6. Remediation check
    streak = crud.get_incorrect_streak(db, body.user_id, body.question_id)
    remediation = None
    if should_remediate(cms, streak):
        remediation = trigger_remediation(concept_name, skill_map)

    return {
        "user_id": body.user_id,
        "question_id": body.question_id,
        "concept": concept_name,
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "cms": cms,
        "old_skill": old_skill,
        "new_skill": new_skill,
        "skill_delta": round(new_skill - old_skill, 2),
        "remediation": remediation,
        "message": (
            "Correct! Well done!" if is_correct
            else ("Remediation triggered — check the lesson below!" if remediation
                  else "Not quite — review the explanation below.")
        ),
    }


# ── Adaptive-start: backend picks the weakest topic automatically ──────────────

class AdaptiveStartRequest(BaseModel):
    user_id: int
    n: int = 5


@router.post("/adaptive-start")
def adaptive_start(body: AdaptiveStartRequest, db: Session = Depends(get_db)):
    """
    Pure weak-focus session:
      1. Load full skill vector for the user
      2. Pick the concept with lowest ELO (unseen concepts = 1000, treated as neutral)
      3. Delegate to the same logic as /start
    """
    all_concepts = get_all_concepts()
    skill_map = crud.get_all_skills(db, body.user_id)

    # Score each concept: lower ELO → higher priority
    # Never-attempted concepts default to 1000 (neutral, not prioritised over weak ones)
    scored = []
    for concept in all_concepts:
        elo = skill_map.get(concept, 1000.0)
        scored.append((elo, concept))

    scored.sort(key=lambda x: x[0])  # ascending → weakest first

    # Pick the weakest concept that actually has questions in the DB
    chosen_topic = None
    for elo, concept in scored:
        if crud.count_questions_by_subtopic(db, concept) > 0:
            chosen_topic = concept
            break

    if not chosen_topic:
        raise HTTPException(status_code=404, detail="No questions found in DB. Run seed first.")

    # Reuse start_session logic
    return start_session(
        PracticeStartRequest(user_id=body.user_id, topic=chosen_topic, n=body.n),
        db,
    )
