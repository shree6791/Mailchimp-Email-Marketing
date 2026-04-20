"""Smoke tests for Streamlit dashboard filter logic (pure pandas)."""

import pandas as pd

from src.constants.insights import OUTSIDE_LLM_TOP_N_SUMMARY
from src.serving.streamlit.dashboard_filters import (
    TrendDashboardFilters,
    apply_trend_dashboard_filters,
)


def _minimal_insights() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trend_type": ["entertainment", "technology", "entertainment"],
            "marketing_safe": [True, False, None],
            "fragmented_trend": [False, False, True],
            "summary": [
                "Real summary A",
                "Real summary B",
                OUTSIDE_LLM_TOP_N_SUMMARY,
            ],
            "opportunity_score": [80.0, 50.0, 30.0],
        }
    )


def test_campaign_ready_only_filters() -> None:
    df = _minimal_insights()
    f = TrendDashboardFilters(
        category="All",
        campaign_readiness="Campaign Ready Only",
        clarity="All",
        show_all_topics_including_non_llm=True,
        sort_column="opportunity_score",
        page_size=6,
    )
    out = apply_trend_dashboard_filters(df, f)
    assert len(out) == 1
    assert out.iloc[0]["marketing_safe"] is True


def test_llm_summaries_only_excludes_placeholder() -> None:
    df = _minimal_insights()
    f = TrendDashboardFilters(
        category="All",
        campaign_readiness="All",
        clarity="All",
        show_all_topics_including_non_llm=False,
        sort_column="opportunity_score",
        page_size=6,
    )
    out = apply_trend_dashboard_filters(df, f)
    assert len(out) == 2
    assert OUTSIDE_LLM_TOP_N_SUMMARY not in out["summary"].tolist()
