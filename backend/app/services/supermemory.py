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

    Searches for past session summaries and derives:
      weak_concepts, hint_dependency from stored metadata.
    Falls back to empty defaults if no memory exists yet.
    """
    if not settings.supermemory_api_key:
        return _default_state()

    try:
        response = httpx.get(
            f"{BASE_URL}/documents",
            headers=_headers(),
            params={"q": f"user_id:{user_id} Attempted", "limit": 10},
            timeout=3.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", data.get("documents", []))

        if not results:
            return _default_state()

        # Mine metadata from stored session summaries
        weak_concepts: set[str] = set()
        hint_count = 0
        total = 0
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("is_correct") == "False":
                concept = meta.get("concept", "")
                if concept and concept != "unknown":
                    weak_concepts.add(concept.replace("_", " "))
            if meta.get("hint_used") == "True":
                hint_count += 1
            total += 1

        hint_dep = "low"
        if total > 0 and hint_count / total > 0.5:
            hint_dep = "high"
        elif total > 0 and hint_count / total > 0.25:
            hint_dep = "medium"

        return {
            "weak_concepts": list(weak_concepts)[:5],  # top 5 weak areas
            "slow_solver": False,
            "hint_dependency": hint_dep,
        }
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


def format_learner_context(state: dict) -> str:
    """
    Convert a learner state dict into a plain-English paragraph
    that can be injected into any Gemini prompt to personalise it.
    Returns an empty string if no meaningful state exists.
    """
    parts = []
    weak = state.get("weak_concepts", [])
    if weak:
        parts.append(f"The learner struggles with: {', '.join(weak)}.")
    if state.get("slow_solver"):
        parts.append("They tend to solve slowly — prefer step-by-step explanations.")
    hint_dep = state.get("hint_dependency", "low")
    if hint_dep in ("medium", "high"):
        parts.append(f"They have {hint_dep} hint dependency — guide them to think independently.")
    return " ".join(parts)


def get_learner_context_string(user_id: int) -> str:
    """
    Fetch Supermemory for a user and return a prompt-ready string.
    Returns empty string if no memory or on error.
    """
    if not settings.supermemory_api_key:
        return ""
    try:
        response = httpx.get(
            f"{BASE_URL}/memories/search",
            headers=_headers(),
            params={"q": f"user {user_id} learning behaviour weak concepts", "limit": 3},
            timeout=8.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", data.get("documents", []))
        if not results:
            return ""
        # Concatenate the most relevant memory snippets (up to 400 chars total)
        snippets = []
        total = 0
        for r in results:
            content = r.get("content", r.get("text", ""))
            if content and total < 400:
                snippets.append(content[:200])
                total += len(content)
        return " | ".join(snippets) if snippets else ""
    except Exception as e:
        print(f"[Supermemory] get_learner_context_string error: {e}")
        return ""
