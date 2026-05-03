import sqlite3
import os
from typing import Any


def ranker_tool(scored_candidates: list[dict[str, Any]], top_n: int = 3) -> list[dict[str, Any]]:
    """
    Ranks a list of scored candidates by their match score in descending order
    and assigns SHORTLISTED or REJECTED status labels.

    This tool sorts candidates from highest to lowest score, assigns each a
    rank number starting from 1, and labels the top `top_n` candidates as
    'Shortlisted' and the remainder as 'Rejected'.

    Args:
        scored_candidates: A list of candidate dicts from Agent 2, each containing:
            - name (str): Full name of the candidate.
            - email (str): Email address of the candidate.
            - score (float): Match score between 0 and 100.
            - reasoning (str): Explanation of the score from the Job Matcher.
        top_n: Number of top candidates to shortlist. Defaults to 3.

    Returns:
        A list of ranked candidate dicts, each containing:
            - rank (int): Position in the ranking (1 = highest score).
            - name (str): Full name of the candidate.
            - email (str): Email address of the candidate.
            - score (float): Match score between 0 and 100.
            - status (str): 'Shortlisted' for top_n candidates, 'Rejected' otherwise.
            - reasoning (str): Explanation carried over from the Job Matcher.

    Raises:
        ValueError: If scored_candidates is empty or top_n is less than 1.
        KeyError: If a candidate dict is missing required fields.
        TypeError: If score values are not numeric.

    Example:
        >>> candidates = [
        ...     {"name": "Alice", "email": "alice@example.com", "score": 87.5, "reasoning": "Strong Python skills"},
        ...     {"name": "Bob",   "email": "bob@example.com",   "score": 62.0, "reasoning": "Some experience"},
        ...     {"name": "Carol", "email": "carol@example.com", "score": 91.0, "reasoning": "Excellent match"},
        ... ]
        >>> results = ranker_tool(candidates, top_n=2)
        >>> results[0]["name"]
        'Carol'
        >>> results[0]["status"]
        'Shortlisted'
        >>> results[2]["status"]
        'Rejected'
    """
    if not scored_candidates:
        raise ValueError("scored_candidates list is empty — no candidates to rank.")

    if top_n < 1:
        raise ValueError(f"top_n must be at least 1, got {top_n}.")

    # Validate required fields and types
    required_fields = {"name", "email", "score", "reasoning"}
    for i, candidate in enumerate(scored_candidates):
        missing = required_fields - candidate.keys()
        if missing:
            raise KeyError(
                f"Candidate at index {i} is missing required fields: {missing}"
            )
        if not isinstance(candidate["score"], (int, float)):
            raise TypeError(
                f"Candidate '{candidate['name']}' has non-numeric score: {candidate['score']!r}"
            )

    # Sort by score descending
    sorted_candidates = sorted(
        scored_candidates,
        key=lambda c: c["score"],
        reverse=True
    )

    # Assign rank and status
    ranked: list[dict[str, Any]] = []
    for i, candidate in enumerate(sorted_candidates):
        rank = i + 1
        status = "Shortlisted" if i < top_n else "Rejected"
        ranked.append({
            "rank":      rank,
            "name":      candidate["name"],
            "email":     candidate["email"],
            "score":     candidate["score"],
            "status":    status,
            "reasoning": candidate.get("reasoning", ""),
        })

    return ranked