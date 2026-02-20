"""
Aryabhata 1.0 client — PhysicsWallahAI/Aryabhata-1.0

JEE-Math-tuned 7B model (86%+ on JEE Mains 2025).

Uses HuggingFace Serverless Inference API (/v1/chat/completions).
Requires: HF_TOKEN in .env (free at https://huggingface.co/settings/tokens)

Falls back to Gemini if HF_TOKEN is not set or call fails.
"""

import re
import httpx

from app.config import settings

HF_MODEL = "PhysicsWallahAI/Aryabhata-1.0"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are Aryabhata, an expert mathematics tutor for JEE (Joint Entrance Exam). "
    "Solve the problem step-by-step. Show each step clearly numbered. "
    "At the end, put the final answer inside \\boxed{}. "
    "Be concise but thorough."
)


def _call_aryabhata(question: str) -> str | None:
    """Call HuggingFace Serverless Inference API for Aryabhata-1.0."""
    if not settings.hf_token:
        return None

    try:
        response = httpx.post(
            HF_API_URL,
            headers={
                "Authorization": f"Bearer {settings.hf_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": HF_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Aryabhata] API error: {e}")
        return None


def _parse_aryabhata_response(raw: str) -> dict:
    """
    Parse Aryabhata output into steps + final_answer.

    Aryabhata outputs either:
      - <think>...</think> reasoning blocks
      - Plain numbered step-by-step
      - Final answer in \\boxed{...}
    """
    # Strip <think>...</think> wrapper if present (chain-of-thought block)
    think_match = re.search(r"<think>(.*?)</think>", raw, re.DOTALL)
    if think_match:
        think_content = think_match.group(1).strip()
        # The answer is usually after </think>
        after_think = raw[think_match.end():].strip()
        raw_for_steps = think_content
        raw_for_answer = after_think or think_content
    else:
        raw_for_steps = raw
        raw_for_answer = raw

    # Extract final answer from \boxed{...}
    boxed = re.findall(r"\\boxed\{([^}]+)\}", raw_for_answer)
    final_answer = boxed[-1] if boxed else ""

    # If no boxed found try "Final Answer: ..." pattern
    if not final_answer:
        m = re.search(r"(?:final answer|answer)[:\s]+([^\n.]+)", raw_for_answer, re.IGNORECASE)
        if m:
            final_answer = m.group(1).strip()

    # Extract numbered steps
    step_patterns = re.findall(
        r"(?:Step\s*\d+[:.]?|^\d+[.)]\s*)(.+?)(?=(?:Step\s*\d+|^\d+[.)]|\Z))",
        raw_for_steps,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if step_patterns:
        steps = [s.strip().replace("\n", " ") for s in step_patterns if s.strip()]
    else:
        # Fallback: split by double newline → paragraphs as steps
        paragraphs = [p.strip() for p in raw_for_steps.split("\n\n") if p.strip()]
        steps = paragraphs[:8]  # cap at 8

    # Remove any boxed markers from steps for readability
    steps = [re.sub(r"\\boxed\{([^}]+)\}", r"\1", s) for s in steps]

    return {
        "steps": steps if steps else [raw[:500]],
        "final_answer": final_answer or "See steps above.",
        "model_used": "aryabhata-1.0",
    }


def solve_with_aryabhata(question: str) -> dict | None:
    """
    Try to solve using Aryabhata 1.0.
    Returns parsed dict or None if unavailable/failed.
    """
    raw = _call_aryabhata(question)
    if raw is None:
        return None
    return _parse_aryabhata_response(raw)
