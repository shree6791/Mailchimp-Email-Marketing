"""Streamlit dashboard: sort keys, filter option labels, trend display strings."""

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
    "technology": ("#DBEAFE", "#1D4ED8"),
    "beauty_lifestyle": ("#FCE7F3", "#BE185D"),
    "entertainment": ("#EDE9FE", "#6D28D9"),
    "food": ("#FEF3C7", "#B45309"),
    "seasonal": ("#DCFCE7", "#15803D"),
    "general": ("#E5E7EB", "#374151"),
}
