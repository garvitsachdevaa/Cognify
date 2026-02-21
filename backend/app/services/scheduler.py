"""
Background scheduler — runs nightly to keep the question bank fresh.

Jobs:
  - enrich_weak_topics  (every 24h)
      For every topic that has < LOW_STOCK questions in Postgres,
      call ingest_topic() to pull new questions from the web via Tavily + Gemini.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.concept_graph import get_all_concepts
from app.services.ingestion import ingest_topic

logger = logging.getLogger(__name__)

# Trigger ingestion whenever a topic has fewer than this many questions
_MIN_QUESTIONS_PER_TOPIC = 10
_INGEST_BATCH = 8   # how many new questions to fetch per run


def _enrich_weak_topics() -> None:
    """Fetch Postgres connection inside the job to avoid cross-thread session issues."""
    try:
        from app.db import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            all_concepts = get_all_concepts()
            for concept in all_concepts:
                row = db.execute(
                    text("SELECT COUNT(*) FROM questions WHERE subtopics::text ILIKE :s"),
                    {"s": f"%{concept}%"},
                ).fetchone()
                count = int(row[0]) if row else 0
                if count < _MIN_QUESTIONS_PER_TOPIC:
                    logger.info(f"[Scheduler] Enriching '{concept}' (only {count} questions)…")
                    try:
                        new_qs = ingest_topic(concept, n=_INGEST_BATCH)
                        logger.info(f"[Scheduler] Ingested {len(new_qs)} questions for '{concept}'")
                    except Exception as exc:
                        logger.warning(f"[Scheduler] Ingest failed for '{concept}': {exc}")
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"[Scheduler] Job error: {exc}")


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _enrich_weak_topics,
        trigger=IntervalTrigger(hours=24),
        id="enrich_weak_topics",
        name="Nightly question bank enrichment",
        replace_existing=True,
        misfire_grace_time=3600,  # 1h grace window if server was down
    )
    _scheduler.start()
    logger.info("[Scheduler] Started — nightly topic enrichment active.")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped.")
