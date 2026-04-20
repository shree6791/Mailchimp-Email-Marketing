"""Streamlit layout fragments for the trend dashboard."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src.constants.dashboard import TREND_TYPE_BADGE_COLORS
from src.constants.mailchimp_ui import (
    MAILCHIMP_CANVAS,
    MAILCHIMP_SURFACE,
    MAILCHIMP_WHITE,
    MAILCHIMP_YELLOW,
)
from src.serving.streamlit.formatting import compact_number, pill, pretty_trend_type


def render_badges(row: pd.Series) -> None:
    trend_type = row.get("trend_type", "general")
    fragmented = bool(row.get("fragmented_trend", False))
    marketing_safe = row.get("marketing_safe", None)

    bg, fg = TREND_TYPE_BADGE_COLORS.get(trend_type, ("#E5E7EB", "#374151"))

    badges = [
        pill(pretty_trend_type(trend_type), bg, fg),
        pill("Mixed / Noisy", MAILCHIMP_SURFACE, MAILCHIMP_WHITE, border=MAILCHIMP_YELLOW)
        if fragmented
        else pill("Clear", MAILCHIMP_SURFACE, MAILCHIMP_WHITE, border=MAILCHIMP_WHITE),
        pill("Campaign Ready", MAILCHIMP_YELLOW, MAILCHIMP_CANVAS)
        if marketing_safe is True
        else pill("No Campaign", MAILCHIMP_SURFACE, "#A8A29E"),
    ]

    html = "".join(badges)

    st.markdown(
        f"""
<div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:0.35rem 0 0.8rem 0;">
    {html}
</div>
""",
        unsafe_allow_html=True,
    )


def render_statline(row: pd.Series) -> None:
    score = f"{row.get('trend_score', 0):.2f}"
    views = compact_number(row.get("avg_views", 0))
    likes = compact_number(row.get("avg_likes", 0))
    momentum = float(row.get("momentum", 0))
    opportunity = f"{row.get('opportunity_score', 0):.1f}"

    momentum_prefix = "+" if momentum > 0 else ""
    text = (
        f"<span style='color:{MAILCHIMP_WHITE};'>"
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Opportunity</strong> {opportunity}  ·  "
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Trend Strength</strong> {score}  ·  "
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Views</strong> {views}  ·  "
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Likes</strong> {likes}  ·  "
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Growth</strong> {momentum_prefix}{momentum:.2f}"
        f"</span>"
    )
    st.markdown(text, unsafe_allow_html=True)


def render_trend_card(row: pd.Series) -> None:
    topic_name = row.get("topic_display_name", "Unnamed Trend")
    summary = row.get("summary", "")
    suggestion = row.get("campaign_copy", {})
    if not isinstance(suggestion, dict):
        suggestion = {}

    with st.container(border=True):
        st.markdown(f"### {topic_name}")
        render_badges(row)
        render_statline(row)

        st.write(summary)

        if row.get("marketing_safe", False) and suggestion.get("suggested_subject"):
            st.markdown(
                f"**Suggested Subject:** {suggestion.get('suggested_subject', '')}"
            )

        with st.expander("Details"):
            topic_label = row.get("topic_label", "")
            if topic_label:
                st.markdown(f"**Keywords:** {topic_label}")

            dominant_keywords = row.get("dominant_topic_keywords")
            if dominant_keywords:
                st.markdown(
                    f"**Dominant Keywords:** {', '.join(dominant_keywords)}"
                )

            sample_titles = row.get("sample_titles")
            if sample_titles:
                st.markdown("**Sample Titles**")
                for title in sample_titles:
                    st.write(f"- {title}")

            if row.get("marketing_safe", False) and suggestion:
                st.markdown("**Campaign Angle**")
                st.write(suggestion.get("campaign_angle", ""))

                st.markdown("**Email Hook**")
                st.write(suggestion.get("email_hook", ""))
            else:
                st.caption("No campaign suggestion for this trend.")


def render_top_metrics(topic_insights: pd.DataFrame, filtered: pd.DataFrame) -> None:
    a, b, c, d = st.columns(4)
    a.metric("Topics Identified", len(topic_insights))
    b.metric("Top Trends", len(filtered))
    c.metric("Actionable Trends", int((topic_insights["marketing_safe"] == True).sum()))
    d.metric("Noisy Topics", int((topic_insights["fragmented_trend"] == True).sum()))


def render_charts(topic_insights: pd.DataFrame) -> None:
    st.markdown("## Trend Overview")

    summary_df = (
        topic_insights.groupby("trend_type", dropna=False)
        .agg(
            trend_count=("trend_type", "size"),
            avg_opportunity=("opportunity_score", "mean"),
            avg_momentum=("momentum", "mean"),
        )
        .reset_index()
        .sort_values("trend_count", ascending=False)
    )

    summary_df["avg_opportunity"] = summary_df["avg_opportunity"].round(1)
    summary_df["avg_momentum"] = summary_df["avg_momentum"].round(2)

    summary_display = summary_df.rename(
        columns={
            "trend_type": "Trend Category",
            "trend_count": "# Trends",
            "avg_momentum": "Avg Growth",
            "avg_opportunity": "Avg Opportunity Score",
        }
    )

    summary_display["Trend Category"] = summary_display["Trend Category"].apply(
        pretty_trend_type
    )

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown("**Trend Category Summary**")
        st.dataframe(
            summary_display,
            use_container_width=True,
            hide_index=True,
        )

    with right:
        st.markdown("**Top Opportunity Trends**")
        opp_df = topic_insights[
            ["topic_display_name", "opportunity_score"]
        ].copy().sort_values("opportunity_score", ascending=False).head(10)

        bar = (
            alt.Chart(opp_df)
            .mark_bar(color=MAILCHIMP_YELLOW, cornerRadiusEnd=3)
            .encode(
                x=alt.X("opportunity_score:Q", title="Opportunity score"),
                y=alt.Y("topic_display_name:N", sort="-x", title=None),
            )
            .properties(height=260)
            .configure_axis(
                labelColor=MAILCHIMP_WHITE,
                titleColor=MAILCHIMP_WHITE,
                gridColor="rgba(255, 224, 27, 0.12)",
                domainColor="rgba(255, 224, 27, 0.35)",
            )
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(bar, use_container_width=True)


def render_trend_card_grid(filtered: pd.DataFrame) -> None:
    left, right = st.columns(2)
    for i, (_, row) in enumerate(filtered.iterrows()):
        if i % 2 == 0:
            with left:
                render_trend_card(row)
        else:
            with right:
                render_trend_card(row)
