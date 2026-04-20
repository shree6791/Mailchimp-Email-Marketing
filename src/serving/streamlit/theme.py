"""Global Streamlit CSS aligned with Mailchimp canvas + yellow + white."""

from __future__ import annotations

import streamlit as st

from src.constants.mailchimp_ui import (
    MAILCHIMP_CANVAS,
    MAILCHIMP_MUTED_TEXT,
    MAILCHIMP_SURFACE,
    MAILCHIMP_SURFACE_ELEVATED,
    MAILCHIMP_WHITE,
    MAILCHIMP_YELLOW,
)


def inject_mailchimp_theme() -> None:
    """Apply layout CSS after ``st.set_page_config`` (call once per run)."""
    st.markdown(
        f"""
<style>
  /* Root canvas */
  .stApp {{
    background-color: {MAILCHIMP_CANVAS};
  }}
  [data-testid="stAppViewContainer"] > .main {{
    background-color: {MAILCHIMP_CANVAS};
  }}
  [data-testid="stHeader"] {{
    background-color: {MAILCHIMP_CANVAS};
  }}
  [data-testid="stToolbar"] {{
    background-color: {MAILCHIMP_CANVAS};
  }}

  /* Sidebar */
  [data-testid="stSidebar"] {{
    background-color: {MAILCHIMP_SURFACE};
    border-right: 1px solid rgba(255, 224, 27, 0.25);
  }}
  [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {{
    color: {MAILCHIMP_WHITE} !important;
  }}
  [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown p {{
    font-size: 0.96rem !important;
    font-weight: 550 !important;
  }}
  [data-testid="stSidebar"] [data-baseweb="select"] span,
  [data-testid="stSidebar"] [data-baseweb="slider"] * {{
    font-size: 0.95rem !important;
  }}
  [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
    font-size: 1.08rem !important;
    font-weight: 700 !important;
  }}

  /* Typography */
  .main h1, div[data-testid="stMarkdownContainer"] h1 {{
    color: {MAILCHIMP_YELLOW} !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
  }}
  .main h2, .main h3, div[data-testid="stMarkdownContainer"] h2,
  div[data-testid="stMarkdownContainer"] h3 {{
    color: {MAILCHIMP_WHITE} !important;
  }}
  .main .stCaption, [data-testid="stCaption"] {{
    color: {MAILCHIMP_MUTED_TEXT} !important;
  }}
  .main p, .main li {{
    font-size: 1.01rem;
    line-height: 1.55;
  }}

  /* Metrics */
  [data-testid="stMetricValue"] {{
    color: {MAILCHIMP_YELLOW} !important;
    font-size: 1.95rem !important;
    font-weight: 700 !important;
  }}
  [data-testid="stMetricLabel"] {{
    color: {MAILCHIMP_MUTED_TEXT} !important;
    font-size: 0.98rem !important;
    font-weight: 600 !important;
  }}
  [data-testid="stMetricDelta"] {{
    color: {MAILCHIMP_WHITE} !important;
  }}

  /* Bordered cards (trend containers) */
  div[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: {MAILCHIMP_SURFACE_ELEVATED} !important;
    border-color: rgba(255, 224, 27, 0.35) !important;
    border-radius: 12px !important;
  }}
  div[data-testid="stVerticalBlockBorderWrapper"] h3 {{
    font-size: 1.28rem !important;
    font-weight: 650 !important;
  }}

  /* Dataframes */
  [data-testid="stDataFrame"] {{
    border: 1px solid rgba(255, 224, 27, 0.35);
    border-radius: 10px;
    overflow: hidden;
  }}

  /* Expanders */
  details summary {{
    color: {MAILCHIMP_WHITE} !important;
  }}
  .streamlit-expanderHeader {{
    color: {MAILCHIMP_WHITE} !important;
  }}

  /* Alerts */
  div[data-testid="stAlert"] {{
    border-radius: 10px;
  }}

  /* Links */
  a {{
    color: {MAILCHIMP_YELLOW} !important;
  }}
</style>
""",
        unsafe_allow_html=True,
    )
