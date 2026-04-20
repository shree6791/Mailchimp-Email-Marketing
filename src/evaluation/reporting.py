"""Console reporting for proxy NDCG."""

from __future__ import annotations

import pandas as pd

from src.evaluation.metrics import proxy_ndcg


def log_ranking_evaluation(
    topic_insights: pd.DataFrame,
    *,
    ndcg_k: int,
    score_col: str = "trend_score",
) -> None:
    """
    Log proxy NDCG@K (aligned with LLM top-N slice).

    Uses blended proxy gain (CTR recency + volume + momentum) against ``trend_score``.
    """
    print("\nRanking evaluation (before LLM enrichment)")
    print("-" * 60)

    nd = proxy_ndcg(topic_insights, score_col=score_col, k=ndcg_k)
    print("Proxy NDCG (trend_score order vs ideal by blended gain)")
    print("  Interpretation: 1.0 = same ordering as sorting by blended gain; <1.0 = ranker reorders vs blended proxy.")
    for key in ("k", "gain_formula", "score_col", "dcg@k (score order)", "idcg@k (ideal by gain)", "ndcg@k (proxy)"):
        if key in nd:
            print(f"  {key}: {nd[key]}")
    print("-" * 60)
