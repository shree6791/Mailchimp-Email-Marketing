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
)
from src.serving.streamlit.data_loading import load_trend_dashboard_data


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_trend_dashboard_data()


def main() -> None:
    st.set_page_config(
        page_title="Mailchimp Trend Engine",
        page_icon="📈",
        layout="wide",
    )

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
    filtered = apply_trend_dashboard_filters(topic_insights, filters)

    render_top_metrics(topic_insights, filtered)
    st.markdown("")

    render_charts(topic_insights)
    st.markdown("## Trends")

    render_trend_card_grid(filtered)


if __name__ == "__main__":
    main()
