# Saved after Step 3 (combined text + lemmatized ``cleaned_text``), before embeddings / topics.
VIDEOS_TEXT_BEFORE_TOPICS_COLUMNS: tuple[str, ...] = (
    "title",
    "tags",
    "trending_date",
    "views",
    "likes",
    "comment_count",
    "document",
    "cleaned_text",
)

# Per-video export (metrics + topic id); full narratives live in topic_insights CSV.
VIDEOS_WITH_TOPICS_EXPORT_COLUMNS: tuple[str, ...] = (
    "title",
    "tags",
    "trending_date",
    "views",
    "likes",
    "comment_count",
    "topic",
    "topic_confidence",
)

# One row per topic for the dashboard (scoring internals stay in memory only).
TOPIC_INSIGHTS_EXPORT_COLUMNS: tuple[str, ...] = (
    "topic",
    "volume",
    "avg_views",
    "avg_likes",
    "avg_comments",
    "momentum",
    "avg_proxy_ctr_recency",
    "trend_score",
    "topic_keywords",
    "dominant_topic_keywords",
    "topic_label",
    "sample_titles",
    "trend_type",
    "fragmented_trend",
    "topic_display_name",
    "summary",
    "marketing_safe",
    "campaign_copy",
)

VIDEOS_TEXT_BEFORE_TOPICS_FILENAME = "videos_text_before_topics.csv"
VIDEOS_WITH_TOPICS_FILENAME = "videos_with_topics.csv"
TOPIC_INSIGHTS_FILENAME = "topic_insights.csv"
