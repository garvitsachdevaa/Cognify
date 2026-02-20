# Adaptive AI EdTech — Exact Runtime Workflow (Full JEE Maths)

> This document describes the **end-to-end runtime workflow** of the adaptive learning system:
> - Where questions come from
> - When LLMs are called
> - What is stored where (Supermemory / Postgres / Pinecone)
> - How outputs are generated
> - How the system adapts over time
> - How this differs from GPT-based study tools

---

## 🧱 Storage Layer Roles

| System        | Stores                                      | Used For                                  |
|--------------|----------------------------------------------|-------------------------------------------|
| **Supermemory** | Persistent learner behavior summaries         | Long-term personalization                  |
| **Postgres**    | Structured skill vector & concept graph      | CMS/ELO updates & remediation logic       |
| **Pinecone**    | Question embeddings + metadata               | Semantic retrieval of practice questions  |

---

## 🟢 Session Start Workflow

### 1. User Action
User selects:
```
Practice → Calculus → Integration by Parts
```

Frontend sends:
```json
POST /practice/start
{
  "user_id": "U101",
  "topic": "integration_by_parts",
  "n": 10
}
```

---

### 2. Retrieve Learner State (Supermemory)

Backend queries:
```
Supermemory.get(user_id)
```

Returns:
```json
{
  "weak_concepts": ["product_rule"],
  "slow_solver": true,
  "hint_dependency": "high"
}
```

Purpose:
- Understand **WHY** to choose certain questions.

---

### 3. Retrieve Skill Vector (Postgres)

Backend queries:
```
SELECT skill FROM user_skill
WHERE user_id = 'U101' AND concept = 'integration_by_parts';
```

Returns:
```
skill = 1180
```

Purpose:
- Match question difficulty to ability.

---

## 🔍 Question Selection Workflow

### 4. Query Pinecone First (Cache-First)

Backend queries:
```json
Pinecone.query({
  subtopic: "integration_by_parts",
  difficulty: ~1180
})
```

#### Case A: Enough Questions Found
- Serve directly.
- **NO LLM call**
- **NO Web Search**

#### Case B: Not Enough Questions
Proceed to ingestion.

---

## 🌐 Ingestion Workflow (Only for New Questions)

### 5. Web Search

Generate queries:
```
"integration by parts JEE problems"
"substitution vs parts JEE examples"
```

Fetch top links via Tavily/Bing/SerpAPI.

---

### 6. Extract Question

Parse HTML → Normalize:
```
∫ x e^x dx
```

Deduplicate via text hash.

---

### 7. LLM Classification (Ingestion-Time Only)

Call LLM with taxonomy:
```text
Classify the subtopics and difficulty (1-5) required to solve:
"∫ x e^x dx"
Return JSON only.
```

LLM returns:
```json
{
  "subtopics": ["integration_by_parts"],
  "difficulty": 3
}
```

---

### 8. Index into Pinecone

Compute embedding → Upsert:
```json
{
  "question_id": "Q123",
  "subtopics": ["integration_by_parts"],
  "difficulty": 3,
  "source_url": "..."
}
```

> Future sessions can now retrieve this **without LLM calls**.

---

## 🟡 Attempt Workflow

### 9. User Attempts Question

Frontend sends:
```json
POST /practice/answer
{
  "user_id": "U101",
  "question_id": "Q123",
  "is_correct": false,
  "time_taken": 52,
  "retries": 1,
  "hint_used": true,
  "confidence": 2
}
```

---

### 10. CMS Calculation (Postgres Logic)

Normalize:
```
accuracy = 0
time_score = clamp(0,1,1 - (time/(1.6*avg_time)))
retry_score = 1/(1+retries)
hint_score = 0
confidence_score = (confidence-1)/4
```

Compute:
```
CMS =
0.45*accuracy +
0.18*time_score +
0.12*retry_score +
0.15*hint_score +
0.10*confidence_score
```

---

### 11. ELO Skill Update (Postgres)

Map difficulty:
```
item_rating = 1000 + (difficulty-1)*200
```

Expected:
```
expected = 1/(1 + 10^((item_rating - skill)/400))
```

Update:
```
new_skill = skill + 20*(CMS - expected)
```

Persist:
```
UPDATE user_skill SET skill = new_skill
```

---

## 🔴 Root-Cause Diagnosis (Concept Graph)

Check prerequisites:
```
integration_by_parts → product_rule
```

Query:
```
SELECT skill FROM user_skill
WHERE user_id='U101' AND concept='product_rule';
```

If low → remediation triggered.

---

## 🟣 Behavior Memory Update (Supermemory)

Generate session note:
```
"User struggles with product rule in integration by parts contexts."
```

Store:
```
Supermemory.write(user_id, summary)
```

Purpose:
- Longitudinal personalization across sessions.

---

## 📚 Remediation Workflow (Teaching)

### 12. LLM Micro-Lesson (On Struggle Only)

Call LLM:
```
Explain product rule in the context of integration by parts in 60 seconds.
```

Return:
- Short explanation
- 2 scaffolded questions

Serve to user.

---

### 13. Guided Practice Retrieval

Fetch from Pinecone:
```
subtopic = product_rule
difficulty ≈ user_skill
```

Serve.

---

## ❓ Doubt Resolution

On user action:
```
POST /doubt
{
  "question_text": "...",
  "student_attempt": "..."
}
```

LLM:
- Step-by-step solution
- Final answer

Verify final numeric result via:
```
sympy
```

Serve verified steps.

---

## 🔁 Closed-Loop Adaptation

Each attempt:
- Updates CMS (Postgres)
- Updates skill vector (Postgres)
- Updates behavior summary (Supermemory)

Next session:
- Supermemory → what learner needs
- Postgres → ability level
- Pinecone → matching content

---

## 📉 LLM Call Policy

| Event                         | LLM Call |
|------------------------------|----------|
Cache hit practice             | ❌       |
User attempts                  | ❌       |
CMS update                     | ❌       |
Skill update                   | ❌       |
Concept diagnosis              | ❌       |
New question ingestion         | ✅       |
Remediation micro-lesson       | ✅       |
Doubt resolution               | ✅       |

---

## 🧠 Why This ≠ GPT Tutor

**GPT Tool:**
```
Input → Answer
```

**This System:**
```
Input
 ↓
CMS Update (Postgres)
 ↓
Prerequisite Check (Concept Graph)
 ↓
Behavior Memory (Supermemory)
 ↓
Targeted Retrieval (Pinecone)
 ↓
Adaptive Output
```

A **Closed-Loop Learning System**.
