"""
Ordered pipeline steps (vision: orchestration / scheduler analog).

Pass a custom ``steps`` sequence to run a prefix/suffix or insert notebook-only steps:
``for label, fn in steps: fn(ctx)``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pandas as pd

from src.schemas.converters import validate_trending_video_rows
from src.storage.writers import save_final_artifacts, save_text_prep_checkpoint


@dataclass
class TrendPipelineContext:
    """Mutable state while running steps (frames may be ``None`` mid-run)."""

    engine: object  # TrendPipelineEngine (avoid circular import)
    videos_df: pd.DataFrame | None = None
    topic_insights_df: pd.DataFrame | None = None


PipelineStep = tuple[str, Callable[[TrendPipelineContext], None]]


def _step_load_dataset(ctx: TrendPipelineContext) -> None:
    ctx.videos_df = ctx.engine.trending_dataset_loader.load()
    validate_trending_video_rows(ctx.videos_df)


def _step_prepare_documents(ctx: TrendPipelineContext) -> None:
    assert ctx.videos_df is not None
    ctx.videos_df = ctx.engine.prepare_documents(ctx.videos_df)


def _step_enrich_documents(ctx: TrendPipelineContext) -> None:
    assert ctx.videos_df is not None
    ctx.videos_df = ctx.engine.enrich_documents(ctx.videos_df)


def _step_save_text_prep_checkpoint(ctx: TrendPipelineContext) -> None:
    assert ctx.videos_df is not None
    save_text_prep_checkpoint(ctx.videos_df, ctx.engine.settings.processed_data_dir)


def _step_assign_topics(ctx: TrendPipelineContext) -> None:
    assert ctx.videos_df is not None
    ctx.videos_df = ctx.engine.assign_topics(ctx.videos_df)


def _step_trend_scoring(ctx: TrendPipelineContext) -> None:
    assert ctx.videos_df is not None
    ctx.topic_insights_df = ctx.engine.score_topic_aggregates(ctx.videos_df)


def _step_attach_topic_keywords(ctx: TrendPipelineContext) -> None:
    assert ctx.videos_df is not None
    assert ctx.topic_insights_df is not None
    ctx.topic_insights_df = ctx.engine.attach_topic_keywords(ctx.topic_insights_df)


def _step_offline_ranking_evaluation(ctx: TrendPipelineContext) -> None:
    assert ctx.topic_insights_df is not None
    ctx.engine.log_topic_ranking_evaluation(ctx.topic_insights_df)


def _step_marketer_insights(ctx: TrendPipelineContext) -> None:
    assert ctx.videos_df is not None
    assert ctx.topic_insights_df is not None
    ctx.topic_insights_df = ctx.engine.enrich_marketer_insights(
        ctx.videos_df,
        ctx.topic_insights_df,
    )


def _step_save_final_artifacts(ctx: TrendPipelineContext) -> None:
    assert ctx.videos_df is not None
    assert ctx.topic_insights_df is not None
    out = save_final_artifacts(
        ctx.videos_df,
        ctx.topic_insights_df,
        ctx.engine.settings.output_dir,
    )
    print(f"Saved final outputs to: {out}")


DEFAULT_TREND_PIPELINE_STEPS: tuple[PipelineStep, ...] = (
    ("Step 1: Load dataset", _step_load_dataset),
    ("Step 2: Build documents", _step_prepare_documents),
    ("Step 3: spaCy normalization (lemmatized text)", _step_enrich_documents),
    ("Step 4: Save text-prep checkpoint (before topics)", _step_save_text_prep_checkpoint),
    ("Step 5: Embeddings + topic assignment", _step_assign_topics),
    ("Step 6: Trend scoring", _step_trend_scoring),
    ("Step 7: Offline ranking evaluation", _step_offline_ranking_evaluation),
    ("Step 8: Attach topic keywords", _step_attach_topic_keywords),
    ("Step 9: Marketer insights", _step_marketer_insights),
    ("Step 10: Save final outputs", _step_save_final_artifacts),
)


def run_trend_pipeline(
    engine: object,
    steps: Sequence[PipelineStep] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run ``steps`` (default: full pipeline).

    Returns ``(videos_with_topics_df, topic_insights_df)`` matching the two output CSVs.
    """
    seq = DEFAULT_TREND_PIPELINE_STEPS if steps is None else tuple(steps)
    ctx = TrendPipelineContext(engine=engine)
    for label, fn in seq:
        print(label)
        fn(ctx)
    assert ctx.videos_df is not None
    assert ctx.topic_insights_df is not None
    return ctx.videos_df, ctx.topic_insights_df
