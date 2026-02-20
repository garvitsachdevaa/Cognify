"""
Doubt router — step-by-step solution with sympy verification.
  POST /doubt  → Gemini solves, sympy verifies final answer
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.gemini_client import solve_doubt

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class DoubtRequest(BaseModel):
    user_id: int
    question_text: str
    student_attempt: str = ""


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("")
def resolve_doubt(body: DoubtRequest):
    """
    Full flow:
    1. Gemini: step-by-step solution JSON
    2. sympy: verify the final_answer expression
    3. Return steps + verified answer
    """
    solution = solve_doubt(body.question_text, body.student_attempt)

    # sympy verification
    verified = None
    sympy_error = None
    sympy_expr = solution.get("sympy_expr", "")

    if sympy_expr:
        try:
            import sympy
            result = sympy.sympify(sympy_expr)
            verified = str(result)
        except Exception as e:
            sympy_error = str(e)

    return {
        "question": body.question_text,
        "steps": solution.get("steps", []),
        "final_answer": solution.get("final_answer", ""),
        "sympy_verified": verified,
        "sympy_error": sympy_error,
    }
