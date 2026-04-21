"""Parse ``trending_date`` strings from regional YouTube trending CSVs (Kaggle formats)."""

from __future__ import annotations

import re

import pandas as pd

from src.utils.text_utils import safe_text


def parse_trending_date_series(series: pd.Series) -> pd.Series:
    """Match Kaggle ``USvideos``-style ``YY.DD.MM`` or fall back to ``pd.to_datetime``."""
    if series.empty:
        return pd.to_datetime(series, errors="coerce")
    sample = safe_text(series.iloc[0])
    if re.match(r"^\d{2}\.\d{2}\.\d{2}$", sample):
        return pd.to_datetime(series, format="%y.%d.%m", errors="coerce")
    return pd.to_datetime(series, errors="coerce")
