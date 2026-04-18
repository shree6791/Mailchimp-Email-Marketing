"""Map clustered keywords to coarse trend_type labels."""

from src.constants.taxonomy import TREND_TYPE_RULES


def classify_trend_type(keywords: list[str], sample_titles: list[str]) -> str:
    text = " ".join(keywords + sample_titles).lower()
    for trend_type, needles in TREND_TYPE_RULES:
        if any(needle in text for needle in needles):
            return trend_type
    return "general"
