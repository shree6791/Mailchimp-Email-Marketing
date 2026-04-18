"""Console reporting for proxy NDCG."""

from __future__ import annotations

import pandas as pd

from src.evaluation.metrics import proxy_ndcg


def log_ranking_evaluation(
    topic_insights: pd.DataFrame,
    *,
    ndcg_k: int,
    gain_col: str = "volume",
    score_col: str = "trend_score",
) -> None:
    """
    Log proxy NDCG@K (aligned with LLM top-N slice).

    Uses ``volume`` and ``trend_score`` only; keyword columns are not required.
    """
    print("\nRanking evaluation (before LLM enrichment)")
    print("-" * 60)

    nd = proxy_ndcg(topic_insights, gain_col=gain_col, score_col=score_col, k=ndcg_k)
    print("Proxy NDCG (trend_score order vs ideal by gain column)")
    print("  Interpretation: 1.0 = same ordering as sorting by gain; <1.0 = ranker reorders vs pure gain.")
    for key in ("k", "gain_col", "score_col", "dcg@k (score order)", "idcg@k (ideal by gain)", "ndcg@k (proxy)"):
        if key in nd:
            print(f"  {key}: {nd[key]}")
    print("-" * 60)
