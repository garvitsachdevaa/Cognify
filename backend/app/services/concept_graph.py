"""
Concept Dependency Graph service.

Loads the static JSON graph from app/data/concept_graph.json.
Provides helpers to:
  - get prerequisites for a concept
  - find the weakest prerequisite for a given user
"""

import json
from functools import lru_cache
from pathlib import Path

GRAPH_PATH = Path(__file__).parent.parent / "data" / "concept_graph.json"


@lru_cache(maxsize=1)
def load_graph() -> dict:
    """Load and cache the concept dependency graph."""
    with open(GRAPH_PATH, "r") as f:
        return json.load(f)


def get_prerequisites(concept: str) -> list[str]:
    """
    Return the direct prerequisites for a concept.

    Example:
        get_prerequisites("integration_by_parts")
        → ["product_rule", "basic_integration"]
    """
    graph = load_graph()
    return graph.get(concept, {}).get("prerequisites", [])


def get_all_concepts() -> list[str]:
    """Return all concept keys defined in the graph."""
    return list(load_graph().keys())


def find_weak_prerequisite(concept: str, skill_map: dict[str, float]) -> str | None:
    """
    Given a concept and a {concept: skill} map, return the weakest prerequisite.
    Returns None if all prerequisites are above 1000 (default baseline).

    Args:
        concept   : the concept the user failed
        skill_map : {concept_name: skill_score}
    """
    prereqs = get_prerequisites(concept)
    if not prereqs:
        return None

    weak = [(p, skill_map.get(p, 1000.0)) for p in prereqs]
    weak.sort(key=lambda x: x[1])

    weakest_concept, weakest_skill = weak[0]
    if weakest_skill < 1000.0:
        return weakest_concept
    return None
