"""
ELO-based skill update.

Maps question difficulty (1–5) to an item rating:
  item_rating = 1000 + (difficulty - 1) * 200

Expected score (logistic):
  expected = 1 / (1 + 10 ** ((item_rating - skill) / 400))

Skill update (K-factor = 20):
  new_skill = skill + 20 * (cms - expected)
"""


def update_skill(skill: float, difficulty: int, cms: float) -> float:
    """
    Return updated ELO skill score.

    Args:
        skill      : current skill rating (e.g. 1000.0)
        difficulty : question difficulty 1–5
        cms        : Cognitive Mastery Score 0.0–1.0

    Returns:
        new_skill  : updated skill rating (float)
    """
    item_rating = 1000 + (difficulty - 1) * 200
    expected = 1.0 / (1.0 + 10 ** ((item_rating - skill) / 400.0))
    new_skill = skill + 20.0 * (cms - expected)
    return round(new_skill, 4)


def get_or_init_skill(db, user_id: int, concept_id: int) -> float:
    """Fetch skill from DB; return default 1000.0 if not found."""
    from app.crud import get_skill
    return get_skill(db, user_id, concept_id)


def persist_skill(db, user_id: int, concept_id: int, new_skill: float) -> None:
    """Upsert skill in DB."""
    from app.crud import upsert_skill
    upsert_skill(db, user_id, concept_id, new_skill)
