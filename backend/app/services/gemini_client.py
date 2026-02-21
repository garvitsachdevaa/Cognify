"""
Google Gemini client.

Free tier (as of 2025):
  - gemini-2.0-flash : 1500 RPD, 15 RPM free tier (AI Studio key required)
  - text-embedding-004: free with quota

Used for:
  1. classify_question()    → subtopics + difficulty (ingestion-time)
  2. generate_lesson()      → 60-second micro-lesson (remediation)
  3. solve_doubt()          → step-by-step solution JSON (doubt resolution)
  4. get_embedding()        → 768-dim vector (indexing + retrieval)
"""

import json
import time

import google.generativeai as genai

from app.config import settings

# Lazy initialization
_model = None
_embed_model = "models/gemini-embedding-001"


def _get_model():
    global _model
    if _model is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel("gemini-flash-latest")
    return _model


def _call_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini with simple exponential-backoff retry on transient errors."""
    for attempt in range(max_retries):
        try:
            model = _get_model()
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt  # 1 s, 2 s …
            print(f"[Gemini] attempt {attempt + 1} failed ({e}), retrying in {wait}s")
            time.sleep(wait)


def get_embedding(text: str) -> list[float]:
    """
    Return 768-dim embedding for the given text using gemini-embedding-001
    with Matryoshka truncation to 768 dims (matches Pinecone index).
    """
    if not settings.gemini_api_key:
        # Return zero vector for testing without API key
        return [0.0] * 768

    genai.configure(api_key=settings.gemini_api_key)
    result = genai.embed_content(
        model=_embed_model,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=768,
    )
    return result["embedding"]


def classify_question(question_text: str) -> dict:
    """
    Classify a question into subtopics and difficulty (1–5).

    Returns:
        {"subtopics": ["integration_by_parts"], "difficulty": 3}
    """
    prompt = f"""You are a JEE Mathematics expert. Classify the following question.

Question: {question_text}

Return ONLY valid JSON with this exact structure:
{{
  "subtopics": ["<concept_key_1>", "<concept_key_2>"],
  "difficulty": <integer 1-5>
}}

Use snake_case concept keys from standard JEE maths topics.
Do not include any explanation, only the JSON."""

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Strip markdown code fences if present
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
    except Exception as e:
        print(f"[Gemini] classify_question error: {e}")
        return {"subtopics": ["unknown"], "difficulty": 3}


def generate_lesson(concept: str) -> str:
    """
    Generate a 60-second micro-lesson for the given concept.

    Returns plain-paragraph explanation with LaTeX math in $...$ delimiters.
    NO markdown formatting (no ##, no **, no bullet dashes).
    """
    concept_label = concept.replace("_", " ")
    prompt = f"""You are a JEE Maths expert tutor. The student is struggling with: {concept_label}

Write a concise 60-second explanation in PLAIN PARAGRAPHS (no markdown, no ### headings, no **bold**, no bullet lists). Use blank lines to separate sections.

Cover:
1. Core idea (2-3 sentences)
2. Key formula or rule
3. One worked example with step-by-step reasoning

Math rules:
- Wrap ALL math in $...$ for inline or $$...$$ for display math on its own line
- Use $^n C_r$ for combinations, $^n P_r$ for permutations
- Use $\\dfrac{{a}}{{b}}$ for fractions
- NEVER use ### headings, **bold**, or - bullet syntax"""

    try:
        return _call_with_retry(prompt)
    except Exception as e:
        print(f"[Gemini] generate_lesson error: {e}")
        return f"Review your notes on {concept_label} and try similar problems to build understanding."


def solve_doubt(question_text: str, student_attempt: str = "") -> dict:
    """
    Generate a step-by-step solution with a verifiable final answer.

    Returns:
        {
            "steps": ["Step 1: ...", "Step 2: ..."],
            "final_answer": "...",
            "sympy_expr": "..."  # optional, for sympy verification
        }
    """
    attempt_section = (
        f"\nStudent's attempt: {student_attempt}" if student_attempt else ""
    )

    prompt = f"""You are a JEE Maths expert. Solve the following problem step-by-step.{attempt_section}

Problem: {question_text}

Return ONLY valid JSON with this exact structure:
{{
  "steps": ["Step 1: ...", "Step 2: ...", "..."],
  "final_answer": "<the final answer — ALWAYS wrap any mathematical expression in $...$ for inline math or $$...$$ for display math, e.g. '$x = \\frac{{1}}{{2}}$' or '$$P(A) = \\frac{{n(A)}}{{n(S)}}$$'>",
  "sympy_expr": "<sympy-compatible Python expression for the final answer, or empty string>"
}}

IMPORTANT: ALL mathematical expressions — in both steps and final_answer — MUST be wrapped in $...$ (inline) or $$...$$ (block). Never output raw LaTeX without $ delimiters.
Be precise. Each step must be clear and numbered."""

    try:
        raw = _call_with_retry(prompt)
        # Strip markdown code fences if present
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
    except Exception as e:
        print(f"[Gemini] solve_doubt error: {e}")
        return {
            "steps": ["[Error generating solution]"],
            "final_answer": "",
            "sympy_expr": "",
        }


def check_answer(question_text: str, user_answer: str) -> dict:
    """
    Check whether a student's answer to a JEE maths question is correct.

    Returns:
        {
            "is_correct": bool,
            "correct_answer": str,
            "explanation": str
        }
    """
    prompt = f"""You are a JEE Mathematics expert grading a student's answer.

Question: {question_text}
Student's answer: {user_answer}

Evaluate whether the student's answer is mathematically correct (accept equivalent forms).

Respond on EXACTLY 3 lines in this format (no extra text, no JSON, no markdown):
CORRECT: yes
ANSWER: <concise correct answer in plain text, e.g. 12 or 1/(1+cosx) or sqrt(169-25)>
REASON: <one plain-text sentence explaining why correct or what was wrong>"""

    try:
        raw = _call_with_retry(prompt).strip()
        result = {"is_correct": False, "correct_answer": "", "explanation": ""}
        for line in raw.splitlines():
            line = line.strip()
            if line.upper().startswith("CORRECT:"):
                val = line.split(":", 1)[1].strip().lower()
                result["is_correct"] = val in ("yes", "true", "correct")
            elif line.upper().startswith("ANSWER:"):
                result["correct_answer"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("REASON:"):
                result["explanation"] = line.split(":", 1)[1].strip()
        # Fallback: if nothing parsed, attempt lenient JSON parse
        if not result["correct_answer"] and "{" in raw:
            try:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                # Escape bare backslashes before parsing
                candidate = raw[start:end]
                import re as _re
                candidate = _re.sub(r'(?<!\\)\\(?![\\"nrtbf/u])', r'\\\\', candidate)
                parsed = json.loads(candidate)
                result["is_correct"] = bool(parsed.get("is_correct", False))
                result["correct_answer"] = str(parsed.get("correct_answer", ""))
                result["explanation"] = str(parsed.get("explanation", ""))
            except Exception:
                pass
        return result
    except Exception as e:
        print(f"[Gemini] check_answer error: {e}")
        return {
            "is_correct": False,
            "correct_answer": "",
            "explanation": "Answer could not be auto-graded — check the correct answer above.",
        }


def generate_hint(question_text: str) -> str:
    """
    Generate a helpful hint for a JEE maths question WITHOUT giving away the answer.
    Returns a single hint string (plain text + KaTeX-wrapped math).
    """
    prompt = f"""You are a JEE Mathematics tutor. A student needs a hint for this problem:

{question_text}

Give ONE clear, helpful hint that guides the student toward the solution without giving away the final answer.
Focus on the key concept, formula, or first step they should use.

Rules:
- ALWAYS wrap any mathematical expression in $...$ for inline math or $$...$$ for display math.
- Use $$...$$ (display math) for standalone formulas like binomial coefficients, fractions, or combinations — NOT inline $...$.
- Use $^nC_r$ notation for combinations (e.g. $^8C_2$) and $^nP_r$ for permutations (e.g. $^8P_2$) — never use \\binom or \\dbinom.
- Use \\dfrac instead of \\frac for fractions so they render readable.
- Limit to 2-3 sentences.
- Do NOT reveal the final numerical answer.
- Return only the hint text, no preamble."""

    try:
        return _call_with_retry(prompt)
    except Exception as e:
        print(f"[Gemini] generate_hint error: {e}")
        return "Think about the key formula or identity relevant to this topic and try applying it step by step."


def generate_questions_for_topic(topic: str, n: int = 5) -> list[dict]:
    """
    Generate n JEE-level practice questions for a topic on the fly.
    Called as a fallback when DB + Pinecone both return empty for a new topic.

    Returns list of dicts: [{"text": str, "difficulty": int}, ...]
    """
    prompt = f"""You are an expert JEE Mathematics problem setter.
Generate exactly {n} JEE-level practice questions for the topic: **{topic.replace('_', ' ')}**.

Each question must:
- Be a clear, self-contained problem (no sub-parts a/b/c)
- Require actual calculation or proof, not just recall
- Use KaTeX-compatible LaTeX wrapped in $...$ for inline or $$...$$ for display math
- Use $^nC_r$ notation for combinations (e.g. $^8C_2$) and $^nP_r$ for permutations — never use \\binom.
- Use \\dfrac instead of \\frac for fractions.
- Vary in difficulty (mix of straightforward and tricky)

Return ONLY a JSON array with exactly {n} objects, each with:
  "text": "<the question string with LaTeX>",
  "difficulty": <integer 1-5>

No extra text, no markdown fences, just the raw JSON array."""

    try:
        raw = _call_with_retry(prompt)
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return []
        return json.loads(raw[start:end])[:n]
    except Exception as e:
        print(f"[Gemini] generate_questions_for_topic error: {e}")
        return []
