"""Display helpers for the Streamlit dashboard (no Streamlit dependency)."""

from src.constants.dashboard import TREND_CATEGORY_LABELS


def pill(text: str, bg: str, fg: str = "#111827") -> str:
    return f"""
<span style="
    display:inline-flex;
    align-items:center;
    padding:0.22rem 0.60rem;
    border-radius:999px;
    background:{bg};
    color:{fg};
    font-size:0.78rem;
    font-weight:600;
    line-height:1.2;
    white-space:nowrap;
">{text}</span>
"""


def compact_number(n: float | int) -> str:
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(int(n))


def pretty_trend_type(value: str) -> str:
    if not value:
        return TREND_CATEGORY_LABELS["general"]
    return TREND_CATEGORY_LABELS.get(value, str(value).replace("_", " ").title())
