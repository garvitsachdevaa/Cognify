"""
Remediation engine.

Decides whether to trigger remediation and orchestrates the flow:
  1. Check CMS threshold
  2. Find weak prerequisite via concept graph
  3. Call Gemini for micro-lesson (LLM call)
  4. Fetch guided practice questions from Pinecone
"""

from app.services.concept_graph import find_weak_prerequisite

CMS_THRESHOLD = 0.5
MAX_INCORRECT_STREAK = 2


def should_remediate(cms: float, incorrect_streak: int) -> bool:
    """
    Return True if remediation should be triggered.

    Triggers when:
      - CMS < 0.5, OR
      - 2+ consecutive incorrect attempts
    """
    return cms < CMS_THRESHOLD or incorrect_streak >= MAX_INCORRECT_STREAK


def trigger_remediation(
    concept: str,
    skill_map: dict[str, float],
    learner_context: str = "",
) -> dict:
    """
    Orchestrate remediation flow.

    Returns a dict with:
      - weak_prereq: the identified weak prerequisite (or None)
      - lesson: micro-lesson text (from Gemini)
      - guided_questions: list of 2 practice questions (from Pinecone)
    """
    from app.services.gemini_client import generate_lesson, get_embedding
    from app.services.pinecone_client import query_questions

    weak_prereq = find_weak_prerequisite(concept, skill_map)
    target = weak_prereq if weak_prereq else concept

    lesson = generate_lesson(target, learner_context=learner_context)

    try:
        emb = get_embedding(target.replace("_", " "))
        guided_questions = query_questions(subtopic=target, query_embedding=emb, n=2)
    except Exception:
        guided_questions = []

    return {
        "weak_prereq": weak_prereq,
        "target_concept": target,
        "lesson": lesson,
        "guided_questions": guided_questions,
    }
