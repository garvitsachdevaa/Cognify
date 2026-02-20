"""
CMS (Cognitive Mastery Score) computation.

Formula:
  CMS = 0.45*accuracy + 0.18*time_score + 0.12*retry_score
        + 0.15*hint_score + 0.10*confidence_score

Inputs:
  is_correct   : bool
  time_taken   : float  (seconds)
  avg_time     : float  (seconds — per-concept average, default 90s for MVP)
  retries      : int
  hint_used    : bool
  confidence   : int (1–5)
"""


def compute_cms(
    is_correct: bool,
    time_taken: float,
    retries: int,
    hint_used: bool,
    confidence: int,
    avg_time: float = 90.0,
) -> float:
    """
    Compute Cognitive Mastery Score (0.0 – 1.0).

    Returns a float clamped to [0, 1].
    """
    accuracy = 1.0 if is_correct else 0.0

    time_score = max(0.0, 1.0 - (time_taken / (1.6 * avg_time)))

    retry_score = 1.0 / (1.0 + retries)

    hint_score = 0.0 if hint_used else 1.0

    confidence_score = (confidence - 1) / 4.0

    cms = (
        0.45 * accuracy
        + 0.18 * time_score
        + 0.12 * retry_score
        + 0.15 * hint_score
        + 0.10 * confidence_score
    )

    return round(min(1.0, max(0.0, cms)), 4)
