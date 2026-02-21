"""
CMS (Cognitive Mastery Score) computation.

Formula:
  CMS = 0.60 * accuracy + 0.25 * time_score + 0.15 * hint_score

accuracy:
  1.0  — correct on first attempt
  0.5  — correct on retry (retries >= 1)
  0.0  — wrong on all attempts

Retries are baked into accuracy (no separate retry component).
Confidence removed — self-reported confidence is unreliable.
"""


def compute_cms(
    is_correct: bool,
    time_taken: float,
    retries: int,
    hint_used: bool,
    avg_time: float = 90.0,
) -> float:
    """
    Compute Cognitive Mastery Score (0.0 – 1.0).

    Returns a float clamped to [0, 1].
    """
    # Accuracy: full credit first try, half credit on retry, none if wrong
    if is_correct and retries == 0:
        accuracy = 1.0
    elif is_correct:
        accuracy = 0.5
    else:
        accuracy = 0.0

    time_score = max(0.0, 1.0 - (time_taken / (1.6 * avg_time)))

    hint_score = 0.0 if hint_used else 1.0

    cms = 0.60 * accuracy + 0.25 * time_score + 0.15 * hint_score

    return round(min(1.0, max(0.0, cms)), 4)
