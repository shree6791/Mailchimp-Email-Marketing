"""Streamlit dashboard: sort keys, filter option labels, trend display strings."""

from src.constants.mailchimp_ui import MAILCHIMP_CANVAS, MAILCHIMP_YELLOW

SORT_OPTIONS: dict[str, str] = {
    "Best Opportunities": "opportunity_score",
    "Trend Strength": "trend_score",
    "Growth Speed": "momentum",
    "Most Viewed": "avg_views",
    "Most Liked": "avg_likes",
    "Highest Volume": "volume",
}

CAMPAIGN_READINESS_OPTIONS = ("All", "Campaign Ready Only", "No Campaign Only")
CLARITY_OPTIONS = ("All", "Clear Topics", "Mixed / Noisy Topics")

TREND_CATEGORY_LABELS: dict[str, str] = {
    "beauty_lifestyle": "Beauty Lifestyle",
    "technology": "Technology",
    "entertainment": "Entertainment",
    "food": "Food",
    "seasonal": "Seasonal",
    "general": "General",
}

TREND_TYPE_BADGE_COLORS: dict[str, tuple[str, str]] = {
    "technology": (MAILCHIMP_YELLOW, MAILCHIMP_CANVAS),
    "beauty_lifestyle": (MAILCHIMP_YELLOW, MAILCHIMP_CANVAS),
    "entertainment": (MAILCHIMP_YELLOW, MAILCHIMP_CANVAS),
    "food": (MAILCHIMP_YELLOW, MAILCHIMP_CANVAS),
    "seasonal": (MAILCHIMP_YELLOW, MAILCHIMP_CANVAS),
    "general": (MAILCHIMP_YELLOW, MAILCHIMP_CANVAS),
}
