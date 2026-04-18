"""
Topic cluster coherence: noise tokens, title/keyword overlap, thematic hints.
"""

from __future__ import annotations

import re

from src.constants.coherence import (
    COHERENCE_THEMATIC_TERMS,
    MIN_DISTINCT_CLEAN_KEYWORDS,
    MIN_THEMATIC_OVERLAP,
)


def looks_like_noise_token(token: str) -> bool:
    if not token:
        return True
    if token.isdigit():
        return True
    if len(token) <= 2:
        return True
    if re.fullmatch(r"\W+", token):
        return True
    return False


def topic_is_coherent(
    keywords: list[str],
    sample_titles: list[str],
    *,
    thematic_terms: frozenset[str] | None = None,
    min_clean_keywords: int = MIN_DISTINCT_CLEAN_KEYWORDS,
    min_thematic_overlap: int = MIN_THEMATIC_OVERLAP,
) -> bool:
    terms = COHERENCE_THEMATIC_TERMS if thematic_terms is None else thematic_terms

    clean_keywords = [k for k in keywords if not looks_like_noise_token(k)]
    if len(clean_keywords) < min_clean_keywords:
        return False

    strong_keywords = [k for k in clean_keywords if len(k) > 3 and not k.isdigit()]
    title_text = " ".join(sample_titles).lower()

    if sum(1 for kw in strong_keywords if kw.lower() in title_text) >= 1:
        return True

    thematic_overlap = sum(1 for kw in strong_keywords if kw.lower() in terms)
    return thematic_overlap >= min_thematic_overlap
