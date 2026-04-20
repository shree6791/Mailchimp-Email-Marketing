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
    page_size: int


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
        index=1,
    )

    clarity = st.sidebar.selectbox(
        "Clarity",
        CLARITY_OPTIONS,
        help=(
            "Whether the video cluster looks coherent or mixed/noisy. This is separate from "
            "whether the LLM wrote the summary (see LLM summaries below)."
        ),
    )

    llm_summaries_mode = st.sidebar.radio(
        "LLM summaries",
        options=("All topics in export", "Full LLM only (top-N)"),
        index=0,
        help=(
            "All topics: include rows where the summary is a placeholder because the topic ranked "
            "below llm_top_n (no model call). Full LLM only: hide those—typically the rows that "
            "received summaries and campaign copy. Use pagination under Trends to browse the list."
        ),
    )
    show_all_topics_including_non_llm = llm_summaries_mode == "All topics in export"

    sort_label = st.sidebar.selectbox(
        "Sort By",
        list(SORT_OPTIONS.keys()),
        index=0,
    )
    sort_column = SORT_OPTIONS[sort_label]

    page_size = st.sidebar.slider(
        "Trends per page",
        min_value=4,
        max_value=24,
        value=6,
        help="How many topic cards to show at once. Use Next/Previous below the chart to browse all matching topics.",
    )

    return TrendDashboardFilters(
        category=category,
        campaign_readiness=campaign_readiness,
        clarity=clarity,
        show_all_topics_including_non_llm=show_all_topics_including_non_llm,
        sort_column=sort_column,
        page_size=page_size,
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
    ).reset_index(drop=True)


def paginate_dataframe(df: pd.DataFrame, page_idx: int, page_size: int) -> pd.DataFrame:
    """Return one page of rows from a sorted dataframe."""
    if df.empty or page_size <= 0:
        return df.iloc[0:0]
    start = page_idx * page_size
    return df.iloc[start : start + page_size]


def max_page_index(n_rows: int, page_size: int) -> int:
    if n_rows <= 0 or page_size <= 0:
        return 0
    return (n_rows - 1) // page_size
