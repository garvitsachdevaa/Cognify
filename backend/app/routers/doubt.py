"""
Doubt router — step-by-step solution with sympy verification.
  POST /doubt        → Gemini solves, sympy verifies
  POST /doubt/solve  → same (alias for frontend)
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.gemini_client import solve_doubt, solve_doubt_with_image

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────────────────

class DoubtRequest(BaseModel):
    user_id: int
    question_text: str = ""
    student_attempt: str = ""
    image_base64: str = ""        # base64-encoded image (optional)
    image_mime_type: str = "image/jpeg"  # mime type of the image


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("")
@router.post("/solve")
def resolve_doubt(body: DoubtRequest):
    """
    Full flow:
    1. If image provided → Gemini Vision solves from image
    2. Else Gemini text solve
    3. sympy: verify the final_answer expression
    4. Return steps + verified answer
    """
    if body.image_base64:
        solution = solve_doubt_with_image(
            body.image_base64,
            body.image_mime_type,
            body.student_attempt,
        )
    elif body.question_text.strip():
        solution = solve_doubt(body.question_text, body.student_attempt)
    else:
        return {
            "question": "",
            "steps": ["Please provide a question text or upload an image."],
            "final_answer": "",
            "sympy_verified": None,
            "sympy_error": None,
        }

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
