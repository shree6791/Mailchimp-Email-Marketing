"""
CLI: load ``topic_insights.csv`` and print the same proxy NDCG as the pipeline log.

Uses blended proxy gain:
  0.5 * ctr_recency_norm + 0.3 * volume_norm + 0.2 * momentum_norm

  python -m src.evaluation [outputs/topic_insights.csv]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.evaluation.metrics import proxy_ndcg


def main() -> int:
    parser = argparse.ArgumentParser(description="Proxy NDCG on topic_insights.csv")
    parser.add_argument(
        "csv_path",
        type=Path,
        nargs="?",
        default=Path("outputs/topic_insights.csv"),
        help="Path to topic_insights.csv",
    )
    parser.add_argument("--k", type=int, default=10, help="Top-K for NDCG (default 10)")
    args = parser.parse_args()

    path = args.csv_path
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows from {path.resolve()}\n")

    nd = proxy_ndcg(df, score_col="trend_score", k=args.k)
    print("Proxy NDCG (trend_score order vs ideal by blended gain)")
    print("  Interpretation: 1.0 = same ordering as sorting by blended gain; <1.0 = ranker reorders vs blended proxy.")
    for key in ("k", "gain_formula", "score_col", "dcg@k (score order)", "idcg@k (ideal by gain)", "ndcg@k (proxy)"):
        if key in nd:
            print(f"  {key}: {nd[key]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
