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

    Returns plain text explanation + 2 scaffolded example problems.
    """
    prompt = f"""You are a JEE Maths expert tutor. The student is struggling with: {concept}

Write a concise 60-second explanation covering:
1. Core idea (2-3 sentences)
2. Key formula or rule
3. One worked example

Keep it focused, clear, and beginner-friendly. Plain text only."""

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini] generate_lesson error: {e}")
        return f"[Error generating lesson for {concept}]"


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
  "final_answer": "<answer as a number or expression>",
  "sympy_expr": "<sympy-compatible Python expression for the final answer, or empty string>"
}}

Be precise. Each step must be clear and numbered."""

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Strip markdown code fences if present
        if "```" in raw:
            # Extract content between first ``` and last ```
            parts = raw.split("```")
            # parts[1] is content inside the first pair of fences
            raw = parts[1].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        # Find JSON object boundaries as fallback
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
