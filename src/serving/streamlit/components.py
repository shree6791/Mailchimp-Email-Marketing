"""Streamlit layout fragments for the trend dashboard."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src.constants.insights import OUTSIDE_LLM_TOP_N_SUMMARY
from src.constants.mailchimp_ui import MAILCHIMP_WHITE, MAILCHIMP_YELLOW
from src.serving.streamlit.formatting import compact_number, pretty_trend_type


def _normalize_campaign_copy(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key in ("campaign_angle", "suggested_subject", "email_hook"):
        v = raw.get(key, "")
        out[key] = str(v) if v is not None else ""
    return out


def _key_phrases_for_details(row: pd.Series) -> str | None:
    """
    Single display line from ``topic_label`` and ``dominant_topic_keywords``.

    Merges when:
    - same wording (after normalizing commas/space); or
    - one's token set is a subset of the other's; or
    - high token overlap (Jaccard) so we do not repeat shared words in ``a · b``.
    """
    tl = str(row.get("topic_label") or "").strip()
    dk_raw = row.get("dominant_topic_keywords")
    dk_s = ""
    if isinstance(dk_raw, list) and dk_raw:
        dk_s = ", ".join(str(x).strip() for x in dk_raw if str(x).strip())

    def norm(s: str) -> str:
        return " ".join(s.lower().replace(",", " ").split())

    def tokens(s: str) -> set[str]:
        return {w for w in norm(s).split() if w}

    if tl and dk_s:
        nt, nd = norm(tl), norm(dk_s)
        if nt == nd:
            return dk_s if len(dk_s) >= len(tl) else tl

        tset, dset = tokens(tl), tokens(dk_s)
        if not tset and not dset:
            pass
        elif not tset:
            return dk_s
        elif not dset:
            return tl
        elif tset <= dset or dset <= tset:
            return dk_s if len(dk_s) >= len(tl) else tl
        else:
            uni = tset | dset
            inter = tset & dset
            jaccard = len(inter) / len(uni) if uni else 0.0
            # Strong overlap but neither is a subset (e.g. each adds one token) → one merged list.
            if jaccard >= 0.55:
                return ", ".join(sorted(uni))

        return f"{tl} · {dk_s}"

    return tl or dk_s or None


def _has_surface_campaign_copy(row: pd.Series, campaign: dict[str, str]) -> bool:
    """Full LLM row with marketing copy blocks (for main card, not placeholder summaries)."""
    if row.get("marketing_safe") is not True:
        return False
    if str(row.get("summary", "")).strip() == OUTSIDE_LLM_TOP_N_SUMMARY:
        return False
    return bool((campaign.get("campaign_angle") or "").strip() or (campaign.get("email_hook") or "").strip())


def _is_featured(row: pd.Series, campaign: dict[str, str]) -> bool:
    """Rows with real LLM summaries and campaign copy (inside top-N), marketing-safe."""
    if str(row.get("summary", "")).strip() == OUTSIDE_LLM_TOP_N_SUMMARY:
        return False
    if row.get("marketing_safe") is not True:
        return False
    return bool((campaign.get("suggested_subject") or "").strip())


def _campaign_unavailable_reason(row: pd.Series) -> str:
    marketing_safe = row.get("marketing_safe", None)
    fragmented = bool(row.get("fragmented_trend", False))
    summary = str(row.get("summary", ""))

    if marketing_safe is False:
        return (
            "Campaign copy not shown: topic is mixed/noisy."
            if fragmented
            else "Campaign copy not shown: topic is not marketing-safe."
        )
    if marketing_safe is None or summary == OUTSIDE_LLM_TOP_N_SUMMARY:
        return "Campaign copy not generated: outside LLM top-N scope."
    return "Campaign copy unavailable for this trend."


def render_statline(row: pd.Series) -> None:
    views = compact_number(row.get("avg_views", 0))
    likes = compact_number(row.get("avg_likes", 0))
    momentum = float(row.get("momentum", 0))
    opportunity = f"{row.get('opportunity_score', 0):.1f}"

    momentum_prefix = "+" if momentum > 0 else ""
    text = (
        f"<span style='color:{MAILCHIMP_WHITE};'>"
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Opportunity</strong> {opportunity}  ·  "
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Views</strong> {views}  ·  "
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Likes</strong> {likes}  ·  "
        f"<strong style='color:{MAILCHIMP_YELLOW};'>Growth</strong> {momentum_prefix}{momentum:.2f}"
        f"</span>"
    )
    st.markdown(text, unsafe_allow_html=True)


def render_trend_card(row: pd.Series) -> None:
    campaign = _normalize_campaign_copy(row.get("campaign_copy"))
    featured = _is_featured(row, campaign)
    topic_name = str(row.get("topic_display_name") or "Unnamed Trend").strip() or "Unnamed Trend"
    subject = (campaign.get("suggested_subject") or "").strip()
    use_subject_headline = bool(
        subject and row.get("marketing_safe") is True and str(row.get("summary", "")).strip() != OUTSIDE_LLM_TOP_N_SUMMARY
    )
    headline = subject if use_subject_headline else topic_name

    summary = row.get("summary", "")

    with st.container(border=True):
        if featured:
            head_l, head_r = st.columns([11, 1])
            with head_l:
                st.markdown(f"### {headline}")
            with head_r:
                st.markdown(
                    '<p title="Full LLM summary and campaign copy for this trend." '
                    'style="text-align:right;font-size:1.35rem;margin:0.1rem 0 0 0;'
                    "padding:0;line-height:1.25;\">🔥</p>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(f"### {headline}")

        render_statline(row)

        surface_campaign = _has_surface_campaign_copy(row, campaign)
        # Narrative summary overlaps angle/hook for marketer-facing rows; keep CSV for full text.
        if not surface_campaign:
            st.write(summary)

        if surface_campaign:
            angle = (campaign.get("campaign_angle") or "").strip()
            hook = (campaign.get("email_hook") or "").strip()
            if angle:
                st.markdown("**Campaign angle**")
                st.write(angle)
            if hook:
                st.markdown("**Email hook**")
                st.write(hook)

        if not use_subject_headline and row.get("marketing_safe", False) and subject:
            st.markdown(f"**Suggested Subject:** {subject}")
        elif not use_subject_headline:
            # Placeholder summary already says LLM was skipped; avoid duplicating below.
            if str(summary).strip() != OUTSIDE_LLM_TOP_N_SUMMARY:
                st.caption(_campaign_unavailable_reason(row))

        kp = _key_phrases_for_details(row)
        sample_titles = row.get("sample_titles")
        if kp or sample_titles:
            with st.expander("Additional context"):
                if kp:
                    st.markdown(f"**Key phrases:** {kp}")
                if sample_titles:
                    st.markdown("**Sample titles**")
                    for title in sample_titles:
                        st.write(f"- {title}")


def render_top_metrics(topic_insights: pd.DataFrame, filtered: pd.DataFrame) -> None:
    """Dataset-level counts only; card count is controlled by sidebar (avoid misleading KPIs)."""
    _ = filtered  # kept for call-site stability with app.py
    a, b = st.columns(2)
    a.metric("Topics identified", len(topic_insights))
    b.metric("Mixed / noisy topics", int((topic_insights["fragmented_trend"] == True).sum()))


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
