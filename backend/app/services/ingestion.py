"""
Question ingestion pipeline.

Flow (triggered only when Pinecone cache is insufficient):
  1. Generate search queries for the topic
  2. Fetch top URLs via Tavily
  3. Parse HTML to extract question text
  4. Deduplicate by SHA-256 hash
  5. Classify via Gemini (subtopics + difficulty)
  6. Compute embedding via Gemini
  7. Upsert into Pinecone + Postgres
"""

import hashlib

import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient

from app.config import settings
from app.services.gemini_client import classify_question, get_embedding
from app.services.pinecone_client import upsert_question


def ingest_topic(topic: str, n: int = 10) -> list[dict]:
    """
    Ingest up to `n` new questions for the given topic from the web.

    Returns a list of ingested question dicts.
    """
    if not settings.tavily_api_key:
        print("[Ingestion] TAVILY_API_KEY not set — skipping web ingestion.")
        return []

    queries = _build_queries(topic)
    raw_questions = []

    tavily = TavilyClient(api_key=settings.tavily_api_key)

    for query in queries:
        try:
            results = tavily.search(
                query=query,
                max_results=5,
                include_raw_content=False,  # summary content is enough + faster
            )
            for result in results.get("results", []):
                url = result.get("url", "")
                # Use full content if available, fall back to snippet
                content = result.get("content", "") or result.get("snippet", "")
                extracted = _extract_questions_from_text(content, url)
                raw_questions.extend(extracted)
                if len(raw_questions) >= n * 2:
                    break
        except Exception as e:
            print(f"[Ingestion] Tavily search error for '{query}': {e}")

    ingested = []
    seen_hashes = set()

    for q in raw_questions:
        text = q["text"].strip()
        if len(text) < 20:
            continue
        # Reject article descriptions before expensive Gemini calls
        text_lower = text.lower()
        if any(p in text_lower for p in (
            "the document", "this document", "pdf includes", "pdf contains",
            "detailing various", "series of", "includes different types",
            "jee main and advanced exam", "practice questions for",
        )):
            continue

        text_hash = hashlib.sha256(text.encode()).hexdigest()
        if text_hash in seen_hashes:
            continue
        seen_hashes.add(text_hash)

        # Classify with Gemini
        classification = classify_question(text)

        # Embed with Gemini
        embedding = get_embedding(text)

        question_id = f"Q_{text_hash[:16]}"

        metadata = {
            "question_id": question_id,
            "text": text[:500],  # Pinecone metadata size limit
            "subtopics": classification.get("subtopics", [topic]),
            "difficulty": classification.get("difficulty", 3),
            "source_url": q.get("source_url", ""),
            "text_hash": text_hash,
        }

        # Upsert into Pinecone
        upsert_question(question_id, embedding, metadata)

        ingested.append(metadata)

        if len(ingested) >= n:
            break

    print(f"[Ingestion] Ingested {len(ingested)} questions for topic: {topic}")
    return ingested


def _build_queries(topic: str) -> list[str]:
    """Generate search query variants for the given topic."""
    readable = topic.replace("_", " ")
    return [
        f"{readable} JEE Mains problems with solutions",
        f"{readable} JEE Advanced practice questions",
        f"solved {readable} problems for JEE Mathematics",
    ]


def _extract_questions_from_text(content: str, source_url: str) -> list[dict]:
    """
    Heuristic extraction of question-like sentences from raw text content.
    Splits on both newlines and sentence boundaries for richer extraction.
    """
    import re

    questions = []

    # Split on lines first, then also on sentence boundaries within long lines
    raw_lines = content.split("\n")
    candidates: list[str] = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        if len(line) > 200:
            parts = re.split(r'(?<=[.?])\s+', line)
            candidates.extend([p.strip() for p in parts if p.strip()])
        else:
            candidates.append(line)

    math_indicators = [
        "∫", "∑", "∏", "√", "→", "≤", "≥", "≠", "∞",
        "$", "^2", "^3", "lim(", "lim_", "dx", "dy", "dz",
        "sin(", "cos(", "tan(", "cot(", "sec(", "log(", "ln(", "f(x)",
        "matrix", "determinant", "vector",
        "eccentricity", "foci", "focus", "ellipse", "parabola", "hyperbola",
        "chord", "tangent", "asymptote", "directrix",
        "integral", "derivative", "differentia", "integra",
        "polynomial", "quadratic", "roots", "coefficient",
        "complex number", "modulus", "argument",
        "probability", "binomial", "permutation", "combination",
        "progression", "sequence", "series",
    ]

    question_starters = (
        "find", "evaluate", "calculate", "compute", "prove", "show", "determine",
        "if ", "let ", "for ", "given", "solve", "integrate", "differentiate",
        "a ", "an ", "the ", "two ", "three ", "suppose", "consider", "from ",
        "which", "what", "how", "when", "using", "without", "in a ", "p(",
    )

    junk_phrases = (
        "the document contains", "this document", "pdf includes", "pdf contains",
        "detailing various", "includes different types", "collection of",
        "set of questions", "click here", "download", "subscribe",
        "all rights reserved", "the following questions",
    )

    seen: set[str] = set()
    for cand in candidates:
        cand = cand.strip()
        if len(cand) < 20 or len(cand) > 600:
            continue
        lower = cand.lower()
        if any(p in lower for p in junk_phrases):
            continue
        key = lower[:60]
        if key in seen:
            continue
        if cand.endswith("?"):
            seen.add(key)
            questions.append({"text": cand, "source_url": source_url})
            continue
        if any(lower.startswith(s) for s in question_starters):
            seen.add(key)
            questions.append({"text": cand, "source_url": source_url})
            continue
        if any(ind in cand for ind in math_indicators):
            seen.add(key)
            questions.append({"text": cand, "source_url": source_url})

    return questions
