"""
Dashboard router — learner overview.
  GET /dashboard/{user_id}  → skill vectors, weak topics, recent history, readiness score
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.db import get_db
from app.services.concept_graph import load_graph

router = APIRouter()


@router.get("/{user_id}")
def get_dashboard(user_id: int, db: Session = Depends(get_db)):
    """
    Returns:
    - skill score per concept (with display names)
    - weak topics (skill < 1000)
    - strong topics (skill > 1100)
    - recent 10 attempts
    - readiness score (avg CMS last 10 attempts)
    """
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    skill_map = crud.get_all_skills(db, user_id)
    recent_attempts = crud.get_recent_attempts(db, user_id, n=10)
    avg_cms = crud.get_avg_cms(db, user_id, n=10)

    graph = load_graph()

    # Enrich skill map with display names
    skills_enriched = []
    for concept_name, skill in skill_map.items():
        node = graph.get(concept_name, {})
        skills_enriched.append({
            "concept": concept_name,
            "display_name": node.get("display_name", concept_name.replace("_", " ").title()),
            "topic": node.get("topic", "General"),
            "skill": skill,
        })
    skills_enriched.sort(key=lambda x: x["skill"])

    weak_topics = [s for s in skills_enriched if s["skill"] < 1000]
    strong_topics = [s for s in skills_enriched if s["skill"] > 1100]

    # Convert attempt datetimes to strings
    for a in recent_attempts:
        if hasattr(a.get("created_at"), "isoformat"):
            a["created_at"] = a["created_at"].isoformat()

    return {
        "user_id": user_id,
        "name": user["name"],
        "readiness_score": avg_cms,
        "total_concepts_practiced": len(skill_map),
        "skill_vector": skills_enriched,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "recent_attempts": recent_attempts,
    }
