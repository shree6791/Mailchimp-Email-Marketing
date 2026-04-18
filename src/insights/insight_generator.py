"""
OpenAI client for trend insights.

**Prompt / rules / schema / fallback copy:** edit ``src/constants/llm_prompts.py`` only.
This module holds transport + JSON shaping helpers (not marketing text).
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from openai import OpenAI

from src.constants.llm_prompts import (
    TREND_INSIGHT_FALLBACK_RESPONSE,
    TREND_INSIGHT_JSON_SCHEMA,
    TREND_INSIGHT_JSON_SCHEMA_NAME,
    TREND_INSIGHT_OUTPUT_KEYS,
    TREND_INSIGHT_PROMPT_TEMPLATE,
)


def _trend_insight_fallback_copy() -> dict[str, Any]:
    """Fresh dict so callers can mutate without touching constants."""
    return dict(TREND_INSIGHT_FALLBACK_RESPONSE)


def _trend_insight_from_parsed_json(data: dict[str, Any]) -> dict[str, Any]:
    return {k: data[k] for k in TREND_INSIGHT_OUTPUT_KEYS}


def _trend_insight_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": TREND_INSIGHT_JSON_SCHEMA_NAME,
        "strict": True,
        "schema": TREND_INSIGHT_JSON_SCHEMA,
    }


class InsightGenerator:
    """Formats prompts from constants, calls the API, parses structured JSON."""

    def __init__(self, model: str):
        self.client = OpenAI()
        self.model = model

    def generate_insight(
        self,
        topic_label: str,
        topic_keywords: list[str],
        trend_type: str,
        row: pd.Series,
        sample_titles: list[str],
    ) -> dict[str, Any]:
        prompt = TREND_INSIGHT_PROMPT_TEMPLATE.format(
            topic_keywords=topic_keywords,
            sample_titles=sample_titles,
            trend_type=trend_type,
            avg_views=int(row["avg_views"]),
            avg_likes=int(row["avg_likes"]),
            momentum=f"{row['momentum']:.2f}",
        )

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": _trend_insight_response_format()},
            )

            text = response.output_text.strip()
            if not text:
                return _trend_insight_fallback_copy()

            data: dict[str, Any] = json.loads(text)
            return _trend_insight_from_parsed_json(data)

        except Exception as exc:
            print(f"LLM insight generation failed for topic '{topic_label}': {exc}")
            return _trend_insight_fallback_copy()
