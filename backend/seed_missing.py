"""
seed_missing.py — Generate and seed questions for all topics that have no
questions in the DB yet.  Uses Gemini to generate 5 JEE-level questions per
missing topic, then inserts them via the same upsert logic as seed_questions.py.

Run from backend/:
    venv/bin/python seed_missing.py
"""

import hashlib, json, sys, time
import google.generativeai as genai
from app.db import SessionLocal
from app.config import settings
import sqlalchemy as sa

# ── Gemini setup ──────────────────────────────────────────────────────────────
genai.configure(api_key=settings.gemini_api_key)
# Use gemini-2.0-flash-lite: separate quota pool from gemini-2.0-flash
model = genai.GenerativeModel("gemini-flash-latest")

# ── Difficulty mapping ────────────────────────────────────────────────────────
TOPIC_DIFFICULTY: dict[str, int] = {
    # Easy/introductory
    "sets_and_operations": 2,
    "power_sets": 2,
    "relations": 2,
    "trig_ratios": 2,
    "trig_identities": 2,
    "straight_lines": 2,
    "matrix_basics": 2,
    "vectors_basics": 2,
    "position_vector": 2,
    "mathematical_induction": 2,
    "harmonic_progression": 2,
    # Medium
    "functions_domain_range": 3,
    "inverse_functions": 3,
    "composition_of_functions": 3,
    "complex_numbers_geometry": 3,
    "permutations": 3,
    "combinations": 3,
    "conditional_probability": 3,
    "inequalities": 3,
    "determinants": 3,
    "inverse_matrix": 3,
    "linear_systems": 3,
    "trig_equations": 3,
    "compound_angles": 3,
    "multiple_angles": 3,
    "inverse_trig": 3,
    "heights_distances": 3,
    "limits": 3,
    "continuity": 3,
    "product_rule": 3,
    "chain_rule": 3,
    "ellipse": 3,
    "hyperbola": 3,
    "basic_integration": 3,
    "integration_by_substitution": 3,
    "dot_product": 3,
    "cross_product": 3,
    "direction_ratios": 3,
    # Hard
    "de_moivre_theorem": 4,
    "implicit_differentiation": 4,
    "higher_order_derivatives": 4,
    "applications_of_derivatives": 4,
    "rolle_mean_value": 4,
    "partial_fractions": 4,
    "definite_integrals": 4,
    "area_under_curves": 4,
    "differential_equations_basics": 4,
    "separable_ode": 4,
    "linear_ode": 4,
    "vector_equation_of_line": 4,
    "vector_equation_of_plane": 4,
    "shortest_distance": 4,
    "angle_between_lines_planes": 4,
}

PROMPT_TEMPLATE = """You are an expert JEE Mathematics problem setter.
Generate exactly 5 JEE-level practice questions for the topic: **{topic}**.

Each question must:
- Be a clear, self-contained problem (no sub-parts a/b/c)
- Require actual calculation or proof, not just recall
- Use KaTeX-compatible LaTeX wrapped in $...$ for inline or $$...$$ for display math
- Use \\dbinom{{n}}{{r}} for combinations and \\dfrac for fractions
- Vary in difficulty (mix of straightforward and tricky)

Return ONLY a JSON array with exactly 5 objects, each with:
  "text": "<the question string with LaTeX>",
  "difficulty": <integer 1-5>

No extra text, no markdown fences, just the raw JSON array."""


def generate_questions_for_topic(topic: str) -> list[dict]:
    prompt = PROMPT_TEMPLATE.format(topic=topic.replace("_", " "))
    for attempt in range(3):
        try:
            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            # Strip markdown fences if Gemini adds them anyway
            if "```" in raw:
                parts = raw.split("```")
                raw = parts[1].strip()
                if raw.lower().startswith("json"):
                    raw = raw[4:].strip()
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1 or end == 0:
                print(f"  [WARN] No JSON array found for {topic}")
                return []
            questions = json.loads(raw[start:end])
            return questions[:5]  # safety cap
        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg.lower():
                wait = 15 * (attempt + 1)
                print(f"  [RATE LIMIT] Waiting {wait}s before retry {attempt+1}/3...")
                time.sleep(wait)
            else:
                print(f"  [ERROR] Gemini call failed for {topic}: {e}")
                return []
    print(f"  [ERROR] All retries exhausted for {topic}")
    return []


def text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def seed():
    db = SessionLocal()

    # Find missing topics
    rows = db.execute(
        sa.text("SELECT DISTINCT jsonb_array_elements_text(subtopics) as t FROM questions")
    ).fetchall()
    seeded_topics = {r[0] for r in rows}

    from app.services.concept_graph import get_all_concepts
    all_concepts = [c for c in get_all_concepts() if c != "_comment"]
    missing = [c for c in all_concepts if c not in seeded_topics]

    print(f"Missing topics: {len(missing)}")

    total_inserted = 0

    for i, topic in enumerate(missing, 1):
        diff = TOPIC_DIFFICULTY.get(topic, 3)
        print(f"[{i}/{len(missing)}] {topic} (difficulty {diff})...", end=" ", flush=True)

        questions = generate_questions_for_topic(topic)
        if not questions:
            print("skipped (no questions)")
            continue

        inserted = 0
        for q in questions:
            text = q.get("text", "").strip()
            if not text:
                continue
            q_diff = q.get("difficulty", diff)
            # Clamp to 1-5
            q_diff = max(1, min(5, int(q_diff)))
            h = text_hash(text)
            try:
                db.execute(
                    sa.text(
                        """INSERT INTO questions (text, subtopics, difficulty, source, text_hash, embedding)
                           VALUES (:text, :subtopics::jsonb, :difficulty, 'gemini_seed', :hash, '[]'::jsonb)
                           ON CONFLICT (text_hash) DO NOTHING"""
                    ),
                    {
                        "text": text,
                        "subtopics": json.dumps([topic]),
                        "difficulty": q_diff,
                        "hash": h,
                    },
                )
                inserted += 1
            except Exception as e:
                print(f"\n  DB error for '{text[:40]}': {e}")
                db.rollback()
                continue

        db.commit()
        total_inserted += inserted
        print(f"{inserted} questions inserted")

        # Small delay to avoid Gemini rate limits
        time.sleep(4)

    db.close()
    print(f"\nDone. Total new questions inserted: {total_inserted}")


if __name__ == "__main__":
    seed()
