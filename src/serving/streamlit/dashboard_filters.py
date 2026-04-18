"""Sidebar widgets (Streamlit) and pure DataFrame filter logic."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.constants.dashboard import (
    CAMPAIGN_READINESS_OPTIONS,
    CLARITY_OPTIONS,
    SORT_OPTIONS,
)
from src.constants.insights import OUTSIDE_LLM_TOP_N_SUMMARY
from src.serving.streamlit.formatting import pretty_trend_type


@dataclass(frozen=True)
class TrendDashboardFilters:
    category: str
    campaign_readiness: str
    clarity: str
    show_all_topics_including_non_llm: bool
    sort_column: str
    top_n: int


def collect_trend_dashboard_filters(topic_insights: pd.DataFrame) -> TrendDashboardFilters:
    st.sidebar.header("Filters")
    st.sidebar.caption(
        "Filter trends to find the most actionable and high-growth opportunities."
    )

    trend_types = ["All"] + sorted(topic_insights["trend_type"].dropna().unique().tolist())
    category = st.sidebar.selectbox(
        "Category",
        trend_types,
        format_func=lambda x: "All" if x == "All" else pretty_trend_type(x),
    )

    campaign_readiness = st.sidebar.selectbox(
        "Campaign Readiness",
        CAMPAIGN_READINESS_OPTIONS,
    )

    clarity = st.sidebar.selectbox("Clarity", CLARITY_OPTIONS)

    show_all_topics_including_non_llm = st.sidebar.checkbox(
        "Show all topics",
        value=False,
    )

    sort_label = st.sidebar.selectbox(
        "Sort By",
        list(SORT_OPTIONS.keys()),
        index=0,
    )
    sort_column = SORT_OPTIONS[sort_label]

    top_n = st.sidebar.slider("Number of Trends", min_value=6, max_value=40, value=10)

    return TrendDashboardFilters(
        category=category,
        campaign_readiness=campaign_readiness,
        clarity=clarity,
        show_all_topics_including_non_llm=show_all_topics_including_non_llm,
        sort_column=sort_column,
        top_n=top_n,
    )


def apply_trend_dashboard_filters(
    topic_insights: pd.DataFrame,
    filters: TrendDashboardFilters,
) -> pd.DataFrame:
    filtered = topic_insights.copy()

    if filters.category != "All":
        filtered = filtered[filtered["trend_type"] == filters.category]

    if filters.campaign_readiness == "Campaign Ready Only":
        filtered = filtered[filtered["marketing_safe"] == True]
    elif filters.campaign_readiness == "No Campaign Only":
        filtered = filtered[filtered["marketing_safe"] == False]

    if filters.clarity == "Clear Topics":
        filtered = filtered[filtered["fragmented_trend"] == False]
    elif filters.clarity == "Mixed / Noisy Topics":
        filtered = filtered[filtered["fragmented_trend"] == True]

    if not filters.show_all_topics_including_non_llm:
        filtered = filtered[
            filtered["summary"].fillna("") != OUTSIDE_LLM_TOP_N_SUMMARY
        ]

    return filtered.sort_values(
        by=filters.sort_column,
        ascending=False,
    ).head(filters.top_n)
