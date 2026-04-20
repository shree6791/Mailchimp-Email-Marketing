"""Proxy NDCG for ranking diagnostics (no human relevance labels)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _minmax_norm(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    smin, smax = float(s.min()), float(s.max())
    if smax <= smin:
        return pd.Series(np.ones(len(s)), index=s.index)
    return (s - smin) / (smax - smin + 1e-12)


def build_blended_gain(df: pd.DataFrame) -> pd.Series:
    """
    Build blended proxy gain used for NDCG relevance.

    gain = 0.5 * ctr_recency_norm + 0.3 * volume_norm + 0.2 * momentum_norm
    """
    required = ("avg_proxy_ctr_recency", "volume", "momentum")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(
            "Need columns for blended gain: "
            f"{missing}. Re-run pipeline to refresh topic_insights.csv with current schema."
        )

    ctr_recency_norm = _minmax_norm(df["avg_proxy_ctr_recency"])
    volume_norm = _minmax_norm(df["volume"])
    momentum_norm = _minmax_norm(df["momentum"])
    return 0.5 * ctr_recency_norm + 0.3 * volume_norm + 0.2 * momentum_norm


def dcg_from_gains(gains: np.ndarray) -> float:
    """DCG with linear gains: sum_i g_i / log2(i+1), i = 1..K (1-based ranks)."""
    gains = np.asarray(gains, dtype=float).flatten()
    if gains.size == 0:
        return 0.0
    i = np.arange(1, len(gains) + 1)
    return float(np.sum(gains / np.log2(i + 1)))


def proxy_ndcg(
    df: pd.DataFrame,
    score_col: str = "trend_score",
    k: int | None = 10,
) -> dict[str, float]:
    """
    Compare ranking by ``score_col`` (descending, as in dashboard) to ideal
    ranking by blended proxy gain:
      0.5 * ctr_recency_norm + 0.3 * volume_norm + 0.2 * momentum_norm

    Returns DCG, IDCG, NDCG for the top-K rows in *current* score order vs ideal.
    """
    if score_col not in df.columns:
        raise KeyError(f"Need column {score_col!r}")

    work = df.copy()
    work["_gain_blended"] = build_blended_gain(work)
    work = work.dropna(subset=["_gain_blended", score_col])
    if work.empty:
        return {"dcg": 0.0, "idcg": 0.0, "ndcg": float("nan"), "k": 0}

    g = work["_gain_blended"].astype(float).values
    gmin, gmax = float(np.min(g)), float(np.max(g))
    if gmax <= gmin:
        rel = np.ones_like(g)
    else:
        rel = (g - gmin) / (gmax - gmin + 1e-12)
        rel = np.clip(rel, 1e-9, 1.0)

    work["_rel"] = rel
    actual = work.sort_values(score_col, ascending=False).reset_index(drop=True)
    ideal = work.sort_values("_gain_blended", ascending=False).reset_index(drop=True)

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
        "gain_formula": "0.5*ctr_recency_norm + 0.3*volume_norm + 0.2*momentum_norm",
        "score_col": score_col,
    }
