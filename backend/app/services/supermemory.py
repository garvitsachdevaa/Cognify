"""
Supermemory.ai client.

REST API wrapper for:
  - get_learner_state(user_id)  → retrieve stored behavioral memory
  - write_session_summary(user_id, summary)  → upsert new summary

Free tier: https://supermemory.ai
API docs: https://docs.supermemory.ai
"""

import httpx

from app.config import settings

BASE_URL = "https://api.supermemory.ai/v3"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.supermemory_api_key}",
        "Content-Type": "application/json",
    }


def get_learner_state(user_id: int) -> dict:
    """
    Retrieve the learner's behavioral memory from Supermemory.

    Returns a dict with keys like:
      weak_concepts, slow_solver, hint_dependency
    Falls back to empty defaults if no memory exists yet.
    """
    if not settings.supermemory_api_key:
        return _default_state()

    try:
        response = httpx.get(
            f"{BASE_URL}/documents",
            headers=_headers(),
            params={"q": f"learner_profile user:{user_id}", "limit": 1},
            timeout=10.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if results:
            # Supermemory stores free-text; we use a simple structured convention
            # TODO: parse actual Supermemory response format
            return results[0].get("metadata", _default_state())
        return _default_state()
    except Exception as e:
        print(f"[Supermemory] get_learner_state error: {e}")
        return _default_state()


def write_session_summary(user_id: int, summary: str, metadata: dict = None) -> bool:
    """
    Store a session behavioral summary for the user.

    Args:
        user_id  : learner identifier
        summary  : natural language summary of the session
        metadata : optional structured dict (weak_concepts, etc.)

    Returns True on success.
    """
    if not settings.supermemory_api_key:
        print("[Supermemory] No API key — skipping write.")
        return False

    payload = {
        "content": summary,
        "metadata": {
            "user_id": str(user_id),
            "type": "session_summary",
            **(metadata or {}),
        },
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/documents",
            headers=_headers(),
            json=payload,
            timeout=10.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[Supermemory] write_session_summary error: {e}")
        return False


def _default_state() -> dict:
    return {
        "weak_concepts": [],
        "slow_solver": False,
        "hint_dependency": "low",
    }
