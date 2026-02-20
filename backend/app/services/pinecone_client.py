"""
Pinecone vector DB client.

Free tier: 1 index, 100k vectors — plenty for MVP.
Index dimension: 768 (Gemini text-embedding-004)

Operations:
  - upsert_question(question_id, embedding, metadata)
  - query_questions(subtopic, difficulty, n) → list of question records
"""

from functools import lru_cache

from pinecone import Pinecone, ServerlessSpec

from app.config import settings

EMBEDDING_DIMENSION = 768
METRIC = "cosine"


@lru_cache(maxsize=1)
def _get_index():
    """Initialize and cache the Pinecone index connection."""
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY not set")

    pc = Pinecone(api_key=settings.pinecone_api_key)

    existing = [idx.name for idx in pc.list_indexes()]
    if settings.pinecone_index_name not in existing:
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=EMBEDDING_DIMENSION,
            metric=METRIC,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"[Pinecone] Created index: {settings.pinecone_index_name}")

    return pc.Index(settings.pinecone_index_name)


def upsert_question(
    question_id: str,
    embedding: list[float],
    metadata: dict,
) -> bool:
    """
    Store a question embedding + metadata in Pinecone.

    Args:
        question_id : unique string ID (e.g. "Q123")
        embedding   : 768-dim float list from Gemini
        metadata    : {"subtopics": [...], "difficulty": int, "source_url": str}
    """
    try:
        index = _get_index()
        index.upsert(vectors=[{"id": question_id, "values": embedding, "metadata": metadata}])
        return True
    except Exception as e:
        print(f"[Pinecone] upsert_question error: {e}")
        return False


def query_questions(
    subtopic: str,
    query_embedding: list[float],
    difficulty: int | None = None,
    n: int = 5,
) -> list[dict]:
    """
    Retrieve questions semantically similar to query_embedding,
    filtered by subtopic (and optionally difficulty).

    Returns list of metadata dicts for matching questions.
    """
    try:
        index = _get_index()
        filter_expr: dict = {"subtopics": {"$in": [subtopic]}}
        if difficulty is not None:
            filter_expr["difficulty"] = {"$eq": difficulty}

        results = index.query(
            vector=query_embedding,
            top_k=n,
            filter=filter_expr,
            include_metadata=True,
        )
        return [match["metadata"] for match in results.get("matches", [])]
    except Exception as e:
        print(f"[Pinecone] query_questions error: {e}")
        return []
