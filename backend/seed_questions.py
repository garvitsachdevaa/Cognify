"""
Seed script — populates Postgres with a baseline set of JEE Maths questions.

Run once:  python seed_questions.py

This lets the demo work even when Gemini/Tavily quota is low.
Questions are based on classic JEE problems across key topics.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.db import SessionLocal

SEED_QUESTIONS = [
    # Calculus — Integration by Parts
    {
        "text": "Evaluate ∫ x·eˣ dx using integration by parts.",
        "subtopics": ["integration_by_parts"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Find ∫ x·sin(x) dx.",
        "subtopics": ["integration_by_parts"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Evaluate ∫ x²·eˣ dx.",
        "subtopics": ["integration_by_parts"],
        "difficulty": 3,
        "source_url": "seed",
    },
    {
        "text": "Find ∫ ln(x) dx.",
        "subtopics": ["integration_by_parts", "basic_integration"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Evaluate ∫ eˣ·cos(x) dx.",
        "subtopics": ["integration_by_parts"],
        "difficulty": 4,
        "source_url": "seed",
    },
    # Calculus — Limits
    {
        "text": "Find lim(x→0) sin(x)/x.",
        "subtopics": ["limits"],
        "difficulty": 1,
        "source_url": "seed",
    },
    {
        "text": "Evaluate lim(x→∞) (1 + 1/x)^x.",
        "subtopics": ["limits"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Find lim(x→0) (eˣ - 1)/x.",
        "subtopics": ["limits"],
        "difficulty": 2,
        "source_url": "seed",
    },
    # Calculus — Differentiation
    {
        "text": "Differentiate f(x) = x²·sin(x) with respect to x.",
        "subtopics": ["product_rule", "differentiation_basics"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Find dy/dx if y = sin(x²) using the chain rule.",
        "subtopics": ["chain_rule"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Find the maxima and minima of f(x) = x³ - 3x + 2.",
        "subtopics": ["applications_of_derivatives"],
        "difficulty": 3,
        "source_url": "seed",
    },
    # Algebra — Quadratic Equations
    {
        "text": "Find the roots of 2x² - 5x + 3 = 0.",
        "subtopics": ["quadratic_equations"],
        "difficulty": 1,
        "source_url": "seed",
    },
    {
        "text": "If α and β are roots of x² - px + q = 0, find α² + β².",
        "subtopics": ["quadratic_equations"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "For what value of k does x² - kx + 4 = 0 have equal roots?",
        "subtopics": ["quadratic_equations"],
        "difficulty": 2,
        "source_url": "seed",
    },
    # Algebra — Complex Numbers
    {
        "text": "Express (3 + 4i)/(1 - 2i) in the form a + bi.",
        "subtopics": ["complex_numbers_basics"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Find the modulus and argument of z = -1 + i.",
        "subtopics": ["complex_numbers_basics"],
        "difficulty": 2,
        "source_url": "seed",
    },
    # Matrices
    {
        "text": "Find the determinant of the matrix [[1,2,3],[0,4,5],[1,0,6]].",
        "subtopics": ["determinants"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Find the inverse of the matrix [[2,1],[5,3]].",
        "subtopics": ["inverse_matrix"],
        "difficulty": 2,
        "source_url": "seed",
    },
    # Trigonometry
    {
        "text": "Prove that sin²θ + cos²θ = 1.",
        "subtopics": ["trig_identities"],
        "difficulty": 1,
        "source_url": "seed",
    },
    {
        "text": "Find all solutions of 2·sin(x) = √3 in [0, 2π].",
        "subtopics": ["trig_equations"],
        "difficulty": 2,
        "source_url": "seed",
    },
    # Vectors
    {
        "text": "Find the angle between vectors a = (1,2,3) and b = (2,-1,1).",
        "subtopics": ["dot_product"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "Find the cross product of vectors a = (1,0,0) and b = (0,1,0).",
        "subtopics": ["cross_product"],
        "difficulty": 1,
        "source_url": "seed",
    },
    {
        "text": "Find the shortest distance between the lines r = (1,2,3) + t(1,0,0) and r = (4,5,6) + s(0,1,0).",
        "subtopics": ["shortest_distance", "vector_equation_of_line"],
        "difficulty": 4,
        "source_url": "seed",
    },
    # Probability
    {
        "text": "A bag has 5 red and 3 blue balls. Two balls are drawn without replacement. Find P(both red).",
        "subtopics": ["basic_probability", "combinations"],
        "difficulty": 2,
        "source_url": "seed",
    },
    {
        "text": "P(A) = 0.4, P(B) = 0.5, P(A∩B) = 0.2. Find P(A|B).",
        "subtopics": ["conditional_probability"],
        "difficulty": 2,
        "source_url": "seed",
    },
    # Coordinate Geometry
    {
        "text": "Find the equation of the circle with centre (3,-2) and radius 5.",
        "subtopics": ["circles"],
        "difficulty": 1,
        "source_url": "seed",
    },
    {
        "text": "Find the focus and directrix of the parabola y² = 12x.",
        "subtopics": ["parabola"],
        "difficulty": 2,
        "source_url": "seed",
    },
]


def seed():
    db = SessionLocal()
    inserted = 0
    skipped = 0

    for q in SEED_QUESTIONS:
        text_hash = hashlib.sha256(q["text"].encode()).hexdigest()
        existing = db.execute(
            __import__("sqlalchemy").text("SELECT id FROM questions WHERE text_hash = :h"),
            {"h": text_hash},
        ).fetchone()

        if existing:
            skipped += 1
            continue

        db.execute(
            __import__("sqlalchemy").text("""
                INSERT INTO questions (text, subtopics, difficulty, source_url, text_hash, embedding_id)
                VALUES (:t, CAST(:st AS jsonb), :d, :url, :h, :eid)
            """),
            {
                "t": q["text"],
                "st": json.dumps(q["subtopics"]),
                "d": q["difficulty"],
                "url": q["source_url"],
                "h": text_hash,
                "eid": "",
            },
        )
        inserted += 1

    db.commit()
    db.close()
    print(f"Seed complete: {inserted} inserted, {skipped} already existed.")


if __name__ == "__main__":
    seed()
