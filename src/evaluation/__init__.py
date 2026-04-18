"""Offline evaluation: proxy NDCG (no labels)."""

from src.evaluation.metrics import dcg_from_gains, proxy_ndcg
from src.evaluation.reporting import log_ranking_evaluation

__all__ = [
    "dcg_from_gains",
    "log_ranking_evaluation",
    "proxy_ndcg",
]
