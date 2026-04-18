"""Write pipeline checkpoints and final CSV artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.schemas.converters import (
    validate_topic_insight_rows,
    validate_video_topic_rows,
)

from src.constants.pipeline_io import (
    TOPIC_INSIGHTS_EXPORT_COLUMNS,
    TOPIC_INSIGHTS_FILENAME,
    VIDEOS_TEXT_BEFORE_TOPICS_COLUMNS,
    VIDEOS_TEXT_BEFORE_TOPICS_FILENAME,
    VIDEOS_WITH_TOPICS_EXPORT_COLUMNS,
    VIDEOS_WITH_TOPICS_FILENAME,
)


def _subset_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    available = [c for c in columns if c in frame.columns]
    return frame[available].copy()


def save_text_prep_checkpoint(videos_df: pd.DataFrame, processed_data_dir: str | Path) -> None:
    processed_dir = Path(processed_data_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    available = [col for col in VIDEOS_TEXT_BEFORE_TOPICS_COLUMNS if col in videos_df.columns]
    videos_df[available].to_csv(
        processed_dir / VIDEOS_TEXT_BEFORE_TOPICS_FILENAME,
        index=False,
    )


def save_final_artifacts(
    videos_with_topics_df: pd.DataFrame,
    topic_insights_df: pd.DataFrame,
    output_dir: str | Path,
) -> Path:
    video_topic_export = _subset_columns(videos_with_topics_df, VIDEOS_WITH_TOPICS_EXPORT_COLUMNS)
    topic_insights_export = _subset_columns(topic_insights_df, TOPIC_INSIGHTS_EXPORT_COLUMNS)

    validate_video_topic_rows(video_topic_export)
    validate_topic_insight_rows(topic_insights_export)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    video_topic_export.to_csv(out / VIDEOS_WITH_TOPICS_FILENAME, index=False)
    topic_insights_export.to_csv(out / TOPIC_INSIGHTS_FILENAME, index=False)
    return out.resolve()
