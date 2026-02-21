"""
Practice router — core session management.
  POST /practice/start   → select topic, retrieve learner state, serve questions
  POST /practice/answer  → record attempt, compute CMS, update skill, maybe remediate
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, Future

from app import crud
from app.db import get_db
from app.services.cms import compute_cms
from app.services.concept_graph import get_all_concepts, load_graph
from app.services.elo import get_or_init_skill, persist_skill, update_skill
from app.services.gemini_client import get_embedding, generate_hint, generate_questions_for_topic
from app.services.ingestion import ingest_topic
from app.services.pinecone_client import query_questions
from app.services.remediation import should_remediate, trigger_remediation
from app.services.supermemory import get_learner_state, write_session_summary, format_learner_context

# Shared thread pool for parallel IO-bound tasks in answer submission
_EXECUTOR = ThreadPoolExecutor(max_workers=4)

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
# (removed: ingest is now synchronous for empty topics — see start_session)


class AnswerRequest(BaseModel):
    user_id: int
    question_id: int
    user_answer: str        # selected option letter (A/B/C/D) for MCQ, numeric string for numerical
    time_taken: float       # seconds
    retries: int = 0        # 0 = first attempt, 1 = second attempt (after retry)
    hint_used: bool = False


# ── Helpers ────────────────────────────────────────────────────────────────────

_QUESTION_STARTERS = (
    "find", "evaluate", "calculate", "compute", "prove", "show", "determine",
    "if ", "let ", "for ", "given", "solve", "integrate", "differentiate",
    "a ", "an ", "the ", "two ", "three ", "four ", "five ",
    "which", "what", "how", "when", "using", "without", "insert", "in a ",
    "from ", "p(", "suppose", "consider",
)

# Phrases that ONLY appear in scraped article/document text, never in real questions
_JUNK_PHRASES = (
    "the document contains",
    "this document contains",
    "pdf includes",
    "pdf contains",
    "detailing various",
    "includes different types of questions",
    "jee main and advanced exams, detailing",
    "collection of questions",
    "set of questions",
)

def _is_valid_question(text: str) -> bool:
    """Return True if text looks like a real JEE math question (not scraped article text)."""
    t = text.strip()
    if not t or len(t) < 15:
        return False
    t_lower = t.lower()
    # Reject known article/document description patterns (very specific phrases only)
    if any(p in t_lower for p in _JUNK_PHRASES):
        return False
    # Reject obviously long article text (real questions are usually < 450 chars)
    if len(t) > 450:
        return False
    # Accept if it ends with "?"
    if t.endswith("?"):
        return True
    # Accept if it starts with a known question word/pattern
    if any(t_lower.startswith(s) for s in _QUESTION_STARTERS):
        return True
    # Accept if it contains LaTeX math markers or math symbols
    if any(marker in t for marker in ["∫", "∑", "∏", "√", "²", "³", "^", "dx", "dy", "$", "\\lim", "\\int", "\\frac", "P("]):
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
    Pinecone-first flow — no hardcoded/seeded questions:
      1. Query Pinecone for existing questions on this topic
      2. If insufficient → run Tavily ingest SYNCHRONOUSLY → re-query Pinecone
      3. Cache Pinecone results in DB (dedup by hash)
      4. Gemini generation as last resort if Tavily also fails
    """
    all_concepts = get_all_concepts()
    if body.topic not in all_concepts:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown topic '{body.topic}'. Valid topics: {all_concepts[:10]}..."
        )

    # 1. Learner state (background — only needed for Gemini fallback)
    learner_state_future: Future = _EXECUTOR.submit(get_learner_state, body.user_id)

    # 2. Skill + difficulty band
    concept_id = _ensure_concept(db, body.topic)
    skill = get_or_init_skill(db, body.user_id, concept_id)
    diff_min, diff_max = _elo_to_difficulty(skill)

    # 3. Seen question IDs — exclude from this session
    seen_ids: set[int] = set(crud.get_seen_question_ids(db, body.user_id, body.topic))

    # 4. Get topic embedding for Pinecone query
    try:
        query_emb = get_embedding(body.topic.replace("_", " "))
    except Exception as e:
        print(f"[Practice] Embedding error: {e}")
        query_emb = None

    def _pinecone_query(n: int) -> list[dict]:
        if not query_emb:
            return []
        try:
            return query_questions(subtopic=body.topic, query_embedding=query_emb, n=n * 2) or []
        except Exception as e:
            print(f"[Practice] Pinecone query error: {e}")
            return []

    def _cache_and_format(hits: list[dict], existing_ids: set[int]) -> tuple[list[dict], set[int]]:
        """Insert Pinecone hits into DB as cache, return valid unseen questions."""
        qs: list[dict] = []
        ids = set(existing_ids)
        for ph in hits:
            text = ph.get("text", "").strip()
            if not text or not _is_valid_question(text):
                continue
            # Parse options from JSON string (Pinecone stores flat metadata)
            raw_opts = ph.get("options", "")
            options = None
            if raw_opts:
                try:
                    options = json.loads(raw_opts)
                except Exception:
                    options = None
            qtype = ph.get("question_type", "numerical")
            correct_option = ph.get("correct_option") or None
            correct_answer = ph.get("correct_answer") or None
            try:
                db_id = crud.insert_question(
                    db,
                    text_=text,
                    subtopics=ph.get("subtopics", [body.topic]),
                    difficulty=int(ph.get("difficulty", 3)),
                    source_url=ph.get("source_url", ""),
                    text_hash=ph.get("text_hash", hashlib.sha256(text.encode()).hexdigest()),
                    embedding_id=ph.get("question_id", ""),
                    question_type=qtype,
                    options=options,
                    correct_option=correct_option,
                    correct_answer=correct_answer,
                )
            except Exception:
                continue
            if db_id in seen_ids or db_id in ids:
                continue
            qs.append({
                "id": db_id,
                "text": text,
                "question_type": qtype,
                "options": options,
                "correct_option": correct_option,
                "correct_answer": correct_answer,
                "subtopics": ph.get("subtopics", [body.topic]),
                "difficulty": int(ph.get("difficulty", 3)),
            })
            ids.add(db_id)
        return qs, ids

    # 5. First Pinecone query
    questions, result_ids = _cache_and_format(_pinecone_query(body.n), set())

    # 6. Not enough in Pinecone → run Tavily ingest SYNCHRONOUSLY, then re-query
    if len(questions) < body.n:
        print(f"[Practice] Only {len(questions)}/{body.n} in Pinecone for '{body.topic}' — running sync ingest...")
        try:
            ingest_topic(body.topic, n=15)
        except Exception as e:
            print(f"[Practice] Ingest failed (non-fatal): {e}")
        more, result_ids = _cache_and_format(_pinecone_query(body.n), result_ids)
        for q in more:
            if q["id"] not in result_ids or q not in questions:
                questions.append(q)
            if len(questions) >= body.n:
                break

    # 7. Still not enough → Gemini generation as absolute last resort
    learner_state: dict = {}
    if len(questions) < body.n:
        try:
            learner_state = learner_state_future.result(timeout=4)
        except Exception:
            pass
        learner_ctx = format_learner_context(learner_state)
        needed = body.n - len(questions)
        print(f"[Practice] Gemini generating {needed} questions for '{body.topic}'...")
        generated = generate_questions_for_topic(body.topic, n=needed, learner_context=learner_ctx)
        for gq in generated:
            text = gq.get("text", "").strip()
            if not text or not _is_valid_question(text):
                continue
            diff = max(1, min(5, int(gq.get("difficulty", 3))))
            qtype = gq.get("question_type", "numerical")
            options = gq.get("options")
            correct_option = gq.get("correct_option")
            correct_answer = gq.get("correct_answer")
            h = hashlib.sha256(text.strip().lower().encode()).hexdigest()
            try:
                db_id = crud.insert_question(
                    db, text_=text, subtopics=[body.topic], difficulty=diff,
                    source_url="gemini_generated", text_hash=h, embedding_id="",
                    question_type=qtype, options=options,
                    correct_option=correct_option, correct_answer=correct_answer,
                )
            except Exception:
                continue
            if db_id not in result_ids:
                questions.append({
                    "id": db_id, "text": text,
                    "question_type": qtype, "options": options,
                    "correct_option": correct_option, "correct_answer": correct_answer,
                    "subtopics": [body.topic], "difficulty": diff,
                })
                result_ids.add(db_id)
    else:
        try:
            learner_state = learner_state_future.result(timeout=4)
        except Exception:
            pass

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
    Direct-match grading — no Gemini needed.
      MCQ:       user_answer (A/B/C/D) == correct_option
      Numerical: abs(float(user_answer) - float(correct_answer)) < 0.01
    CMS: 0.60*accuracy + 0.25*time_score + 0.15*hint_score
    """
    question = crud.get_question_by_id(db, body.question_id)
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {body.question_id} not found")

    # Learner state in background (for remediation personalisation)
    learner_state_future: Future = _EXECUTOR.submit(get_learner_state, body.user_id)

    # ── Direct-match grading ───────────────────────────────────────────────────
    question_type = question.get("question_type", "numerical")

    raw_opts = question.get("options")
    options: dict | None = None
    if raw_opts:
        try:
            options = json.loads(raw_opts) if isinstance(raw_opts, str) else raw_opts
        except Exception:
            options = None

    correct_option     = (question.get("correct_option") or "").strip()
    correct_answer_str = (question.get("correct_answer") or "").strip()

    if question_type == "mcq":
        is_correct = body.user_answer.upper().strip() == correct_option.upper()
        if options and correct_option:
            option_text = options.get(correct_option, "")
            correct_answer_display = f"{correct_option}) {option_text}" if option_text else correct_option
        else:
            correct_answer_display = correct_option
        explanation = "Correct option selected." if is_correct else f"The correct option is {correct_option}."
    else:  # numerical
        try:
            user_val = float(body.user_answer.strip())
            correct_val = float(correct_answer_str)
            is_correct = abs(user_val - correct_val) < 0.01
        except (ValueError, TypeError):
            is_correct = body.user_answer.strip().lower() == correct_answer_str.lower()
        correct_answer_display = correct_answer_str
        explanation = (
            f"Correct! The answer is {correct_answer_str}." if is_correct
            else f"The correct answer is {correct_answer_str}."
        )

    # ── Fast DB ops ────────────────────────────────────────────────────────────
    subtopics = question.get("subtopics") or []
    if isinstance(subtopics, str):
        subtopics = json.loads(subtopics)
    concept_name = subtopics[0] if subtopics else "unknown"
    concept_id   = _ensure_concept(db, concept_name)

    cms = compute_cms(
        is_correct=is_correct,
        time_taken=body.time_taken,
        retries=body.retries,
        hint_used=body.hint_used,
    )

    crud.record_attempt(
        db,
        user_id=body.user_id,
        question_id=body.question_id,
        is_correct=is_correct,
        time_taken=body.time_taken,
        retries=body.retries,
        hint_used=body.hint_used,
        cms=cms,
    )

    difficulty = question.get("difficulty", 3)
    old_skill  = get_or_init_skill(db, body.user_id, concept_id)
    new_skill  = update_skill(old_skill, difficulty, cms)
    persist_skill(db, body.user_id, concept_id, new_skill)

    skill_map = crud.get_all_skills(db, body.user_id)
    skill_map[concept_name] = new_skill

    streak = crud.get_incorrect_streak(db, body.user_id, body.question_id)
    needs_remediation = should_remediate(cms, streak)

    # ── Learner state + Supermemory + remediation ──────────────────────────────
    try:
        learner_state = learner_state_future.result(timeout=4)
    except Exception:
        learner_state = {}
    learner_ctx = format_learner_context(learner_state)

    status  = "correct" if is_correct else "incorrect"
    summary = (
        f"Attempted '{concept_name}' (difficulty {difficulty}). "
        f"Result: {status}. CMS: {cms:.3f}. Skill: {old_skill:.0f} → {new_skill:.0f}. "
        f"Time: {body.time_taken:.0f}s. Hint: {body.hint_used}. Retries: {body.retries}."
    )

    _EXECUTOR.submit(
        write_session_summary,
        body.user_id, summary,
        {"concept": concept_name, "cms": str(cms), "is_correct": str(is_correct)},
    )

    remediation_future: Future | None = None
    if needs_remediation:
        remediation_future = _EXECUTOR.submit(
            trigger_remediation, concept_name, skill_map, learner_ctx
        )

    remediation = None
    if remediation_future is not None:
        try:
            remediation = remediation_future.result(timeout=8)
        except Exception as e:
            print(f"[Remediation] failed (non-fatal): {e}")

    return {
        "user_id":        body.user_id,
        "question_id":    body.question_id,
        "concept":        concept_name,
        "is_correct":     is_correct,
        "correct_answer": correct_answer_display,
        "explanation":    explanation,
        "cms":            cms,
        "old_skill":      old_skill,
        "new_skill":      new_skill,
        "skill_delta":    round(new_skill - old_skill, 2),
        "remediation":    remediation,
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


@router.get("/hint/{question_id}")
def get_hint(question_id: int, db: Session = Depends(get_db)):
    """Return a Gemini-generated hint for the given question without revealing the answer."""
    q = crud.get_question_by_id(db, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    hint_text = generate_hint(q["text"])
    return {"hint": hint_text}
