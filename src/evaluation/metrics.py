"""Proxy NDCG for ranking diagnostics (no human relevance labels)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def dcg_from_gains(gains: np.ndarray) -> float:
    """DCG with linear gains: sum_i g_i / log2(i+1), i = 1..K (1-based ranks)."""
    gains = np.asarray(gains, dtype=float).flatten()
    if gains.size == 0:
        return 0.0
    i = np.arange(1, len(gains) + 1)
    return float(np.sum(gains / np.log2(i + 1)))


def proxy_ndcg(
    df: pd.DataFrame,
    gain_col: str = "volume",
    score_col: str = "trend_score",
    k: int | None = 10,
) -> dict[str, float]:
    """
    Compare ranking by ``score_col`` (descending, as in dashboard) to ideal
    ranking by ``gain_col`` (descending). Gains are min-max scaled to (0,1]
    to avoid scale issues.

    Returns DCG, IDCG, NDCG for the top-K rows in *current* score order vs ideal.
    """
    if gain_col not in df.columns or score_col not in df.columns:
        raise KeyError(f"Need columns {gain_col!r} and {score_col!r}")

    work = df[[gain_col, score_col]].copy()
    work = work.dropna(subset=[gain_col, score_col])
    if work.empty:
        return {"dcg": 0.0, "idcg": 0.0, "ndcg": float("nan"), "k": 0}

    g = work[gain_col].astype(float).values
    gmin, gmax = float(np.min(g)), float(np.max(g))
    if gmax <= gmin:
        rel = np.ones_like(g)
    else:
        rel = (g - gmin) / (gmax - gmin + 1e-12)
        rel = np.clip(rel, 1e-9, 1.0)

    work["_rel"] = rel
    actual = work.sort_values(score_col, ascending=False).reset_index(drop=True)
    ideal = work.sort_values(gain_col, ascending=False).reset_index(drop=True)

    if k is not None:
        actual = actual.head(k)
        ideal = ideal.head(k)

    k_eff = len(actual)
    rel_actual = actual["_rel"].values
    rel_ideal = ideal["_rel"].values

    dcg_a = dcg_from_gains(rel_actual)
    dcg_i = dcg_from_gains(rel_ideal)
    ndcg = dcg_a / dcg_i if dcg_i > 0 else float("nan")

    return {
        "k": float(k_eff),
        "dcg@k (score order)": dcg_a,
        "idcg@k (ideal by gain)": dcg_i,
        "ndcg@k (proxy)": ndcg,
        "gain_col": gain_col,
        "score_col": score_col,
    }
