# Adaptive AI EdTech — Full JEE Maths Sphere Plan

## Executive Summary

We are building an adaptive cognitive engine for the **entire JEE Mathematics syllabus**.

No fine-tuning.  
No model training.  
No paid ML infrastructure.

Everything runs on:
- Runtime LLM prompting
- Cognitive Mastery Score (CMS)
- ELO-based skill updates
- Concept dependency graph
- Persistent learner modeling
- Supermemory for long-term memory

---

# 1️⃣ Complete JEE Maths Coverage

## Algebra
- Quadratic Equations
- Complex Numbers
- Sequences & Series (AP, GP, HP)
- Binomial Theorem
- Permutations & Combinations
- Probability
- Mathematical Induction
- Inequalities

## Matrices & Determinants
- Matrix operations
- Determinants
- Inverse matrix
- Linear systems

## Trigonometry
- Identities
- Equations
- Inverse trig
- Heights & distances

## Coordinate Geometry
- Straight lines
- Circles
- Parabola
- Ellipse
- Hyperbola

## Calculus
- Limits & Continuity
- Differentiation
- Applications of derivatives
- Integration
- Differential equations

## Vectors & 3D Geometry
- Dot/Cross product
- Line & plane equations
- Shortest distance
- Angles

## Sets, Relations & Functions
- Set operations
- Power sets
- Functions & inverses
- Domain & range

---

# 2️⃣ Core Architecture

## Frontend (React / Next.js)
- TopicSelector
- PracticeSession
- QuestionCard
- DoubtChat
- Dashboard

## Backend (FastAPI)
- Question ingestion
- CMS calculation
- Skill updates
- Remediation engine
- Doubt routing

## Storage

### Supermemory (Primary Memory Engine)
Used for:
- Persistent learner profile
- Long-term concept mastery history
- Session summaries
- Adaptive personalization signals

### Postgres
- Users
- Concepts
- Attempts
- Concept graph

### Vector DB (Pinecone / Milvus)
- Question embeddings
- Semantic retrieval

---

# 3️⃣ Live Question Pipeline

1. User selects topic
2. Web search generates problem set
3. HTML parsing extracts question text
4. LLM classifies into:
   - Subtopics
   - Difficulty (1–5)
5. Embeddings stored in vector DB
6. Questions served based on user skill
7. CMS computed per attempt
8. Skill updated
9. Remediation triggered if needed

---

# 4️⃣ Cognitive Mastery Score (CMS)

Inputs:
- Accuracy
- Time taken
- Retries
- Hint usage
- Confidence (1–5)

```python
accuracy = 1 if is_correct else 0
time_score = max(0, 1 - (time_taken/(1.6*avg_time)))
retry_score = 1/(1+retries)
hint_score = 0 if hint_used else 1
confidence_score = (confidence-1)/4

CMS = (
  0.45*accuracy +
  0.18*time_score +
  0.12*retry_score +
  0.15*hint_score +
  0.10*confidence_score
)
```

---

# 5️⃣ Skill Update (ELO-Based)

```python
item_rating = 1000 + (difficulty-1)*200

expected = 1/(1 + 10**((item_rating - skill)/400))

new_skill = skill + 20*(CMS - expected)
```

No training required. Fully deterministic.

---

# 6️⃣ Concept Dependency Graph

Example:

```
vector_equation_of_line → [direction_ratios, dot_product]
direction_ratios → [position_vector]
```

If CMS drops:
- Check prerequisites
- Run targeted diagnostic
- Trigger micro-remediation lesson

---

# 7️⃣ Remediation Flow

Trigger when:
- CMS < 0.5
- 2 incorrect attempts
- Excessive time

System:
1. Identifies weak prerequisite
2. Generates 60-second micro-lesson (LLM)
3. Gives 2 guided problems
4. Re-evaluates CMS

---

# 8️⃣ Doubt Resolution

Using Aryabhata or strong math-capable LLM.

Prompt format:

```
Provide step-by-step solution.
Verify final answer numerically.
Return JSON.
```

Add symbolic/numeric verification via sympy.

---

# 9️⃣ Supermemory Usage

Supermemory stores:
- User skill vector snapshots
- Attempt history summaries
- Long-term weak concept tracking
- Session behavioral signals
- Personalized recommendation context

This replaces Redis for long-term learner memory.

---

# 🔟 Demo Script (Winning Pitch)

“We built a real-time cognitive engine for JEE Maths.

Instead of fixed question banks, we dynamically ingest problems, classify them with LLMs, compute a Cognitive Mastery Score, and update a concept-level skill vector using an ELO-based adaptive model.

The system diagnoses *why* a student fails and remediates prerequisites automatically.”

Show:
- Live CMS update
- Concept graph reasoning
- Remediation trigger
- Skill vector visualization

---

# 11️⃣ 12-Hour Execution Plan

Hour 0–2: Backend skeleton + DB schema  
Hour 2–4: Web ingestion + LLM tagging  
Hour 4–6: Frontend MVP  
Hour 6–8: CMS + skill updates  
Hour 8–9: Doubt endpoint + sympy verification  
Hour 9–10: Concept graph + remediation  
Hour 10–11: Dashboard + readiness score  
Hour 11–12: Deploy + demo recording

---

# 12️⃣ Notes

- Use caching for LLM tagging per question hash.
- Prefer curated sources; fallback to seed bank if scraping fails.
- Visualize internals for judges (skill vector panel).

