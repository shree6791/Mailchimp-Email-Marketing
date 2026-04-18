"""Batch orchestration: ordered steps and ``TrendPipelineEngine`` (vision: scheduler / workflow analog)."""

from src.pipeline.pipeline_run import (
    DEFAULT_TREND_PIPELINE_STEPS,
    TrendPipelineContext,
    run_trend_pipeline,
)
from src.pipeline.trend_engine import TrendPipelineEngine

__all__ = [
    "DEFAULT_TREND_PIPELINE_STEPS",
    "TrendPipelineContext",
    "TrendPipelineEngine",
    "run_trend_pipeline",
]
