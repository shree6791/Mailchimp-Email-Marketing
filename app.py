"""Streamlit entrypoint: thin wiring over ``src.serving.streamlit`` helpers."""

import pandas as pd
import streamlit as st

from src.serving.streamlit.components import (
    render_charts,
    render_top_metrics,
    render_trend_card_grid,
)
from src.serving.streamlit.dashboard_filters import (
    apply_trend_dashboard_filters,
    collect_trend_dashboard_filters,
    max_page_index,
    paginate_dataframe,
)
from src.serving.streamlit.data_loading import load_trend_dashboard_data
from src.serving.streamlit.theme import inject_mailchimp_theme


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_trend_dashboard_data()


def main() -> None:
    st.set_page_config(
        page_title="Mailchimp Trend Engine",
        page_icon="📈",
        layout="wide",
    )

    inject_mailchimp_theme()

    st.title("📈 Mailchimp Trend Engine")
    st.caption(
        "Clean trend intelligence for emerging topics, mixed buzz, and campaign-ready ideas."
    )

    try:
        topic_insights, _ = load_data()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    if topic_insights.empty:
        st.warning("No topic insights found (run the pipeline to build topic_insights.csv).")
        st.stop()

    filters = collect_trend_dashboard_filters(topic_insights)
    filtered_full = apply_trend_dashboard_filters(topic_insights, filters)
    n_topics = len(filtered_full)

    render_top_metrics(topic_insights, filtered_full)
    st.markdown("")

    render_charts(topic_insights)
    st.markdown("## Trends")

    # Pagination: browse all topics that match filters (including non–campaign-ready when allowed).
    page_size = filters.page_size
    max_p = max_page_index(n_topics, page_size)

    filter_sig = (
        filters.category,
        filters.campaign_readiness,
        filters.clarity,
        filters.show_all_topics_including_non_llm,
        filters.sort_column,
    )
    if st.session_state.get("_mailchimp_filter_sig") != filter_sig:
        st.session_state["_mailchimp_filter_sig"] = filter_sig
        st.session_state["mailchimp_trend_page"] = 0

    if "mailchimp_trend_page" not in st.session_state:
        st.session_state["mailchimp_trend_page"] = 0

    page = int(st.session_state["mailchimp_trend_page"])
    page = max(0, min(page, max_p))
    st.session_state["mailchimp_trend_page"] = page

    start_i = page * page_size + 1
    end_i = min((page + 1) * page_size, n_topics)
    st.caption(
        f"Showing topics {start_i}–{end_i} of {n_topics} (page {page + 1} of {max_p + 1}). "
        "Use Previous / Next to see more."
    )

    nav_l, nav_c, nav_r = st.columns([1, 3, 1])
    with nav_l:
        if st.button("◀ Previous", disabled=page <= 0 or n_topics == 0, key="trend_page_prev"):
            st.session_state["mailchimp_trend_page"] = page - 1
    with nav_c:
        st.markdown("")
    with nav_r:
        if st.button("Next ▶", disabled=page >= max_p or n_topics == 0, key="trend_page_next"):
            st.session_state["mailchimp_trend_page"] = page + 1

    page_df = paginate_dataframe(filtered_full, page, page_size)
    render_trend_card_grid(page_df)


if __name__ == "__main__":
    main()
