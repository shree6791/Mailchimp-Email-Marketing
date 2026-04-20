"""
Typed shapes for the batch CSV pipeline.

Models mirror raw input columns (after loader projection), the slim
``videos_with_topics.csv`` / ``topic_insights.csv`` export columns, and what Streamlit consumes.
Use ``src.schemas.converters`` to validate ``pandas`` rows at load and save boundaries.
HTTP request/response models live in ``src.schemas.http_models`` (built on ``TopicInsightRow`` where applicable).
"""
