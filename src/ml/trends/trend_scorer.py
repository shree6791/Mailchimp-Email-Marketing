import re

import numpy as np
import pandas as pd

from src.utils.text_utils import safe_text


class TrendScorer:
    @staticmethod
    def normalize_series(series: pd.Series) -> pd.Series:
        if series.nunique(dropna=False) <= 1:
            return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - series.min()) / (series.max() - series.min() + 1e-9)

    @staticmethod
    def parse_trending_date(series: pd.Series) -> pd.Series:
        sample = safe_text(series.iloc[0]) if len(series) else ""
        if re.match(r"^\d{2}\.\d{2}\.\d{2}$", sample):
            return pd.to_datetime(series, format="%y.%d.%m", errors="coerce")
        return pd.to_datetime(series, errors="coerce")

    def score(self, videos_df: pd.DataFrame) -> pd.DataFrame:
        valid = videos_df[videos_df["topic"] != -1].copy()
        if valid.empty:
            return pd.DataFrame()

        valid["engagement"] = (
            np.log1p(valid["views"].clip(lower=0))
            + 0.7 * np.log1p(valid["likes"].clip(lower=0))
            + 0.4 * np.log1p(valid["comment_count"].clip(lower=0))
        )

        valid["date"] = self.parse_trending_date(valid["trending_date"])
        valid = valid.dropna(subset=["date"])
        if valid.empty:
            return pd.DataFrame()

        daily_counts = (
            valid.groupby(["topic", "date"])
            .size()
            .reset_index(name="doc_count")
        )

        all_dates = sorted(daily_counts["date"].dropna().unique())
        latest_date = all_dates[-1]
        prev_date = all_dates[-2] if len(all_dates) >= 2 else latest_date

        prev_counts = (
            daily_counts[daily_counts["date"] == prev_date][["topic", "doc_count"]]
            .rename(columns={"doc_count": "prev_doc_count"})
        )
        latest_counts = (
            daily_counts[daily_counts["date"] == latest_date][["topic", "doc_count"]]
            .rename(columns={"doc_count": "latest_doc_count"})
        )

        topic_stats = (
            valid.groupby("topic")
            .agg(
                volume=("topic", "size"),
                avg_views=("views", "mean"),
                avg_likes=("likes", "mean"),
                avg_comments=("comment_count", "mean"),
                avg_engagement=("engagement", "mean"),
            )
            .reset_index()
        )

        topic_stats = topic_stats.merge(prev_counts, on="topic", how="left")
        topic_stats = topic_stats.merge(latest_counts, on="topic", how="left")
        topic_stats[["prev_doc_count", "latest_doc_count"]] = (
            topic_stats[["prev_doc_count", "latest_doc_count"]].fillna(0)
        )

        topic_stats["momentum"] = (
            (topic_stats["latest_doc_count"] - topic_stats["prev_doc_count"])
            / (topic_stats["prev_doc_count"] + 1.0)
        )

        topic_stats["volume_norm"] = self.normalize_series(topic_stats["volume"])
        topic_stats["engagement_norm"] = self.normalize_series(
            topic_stats["avg_engagement"]
        )
        topic_stats["momentum_norm"] = self.normalize_series(topic_stats["momentum"])

        topic_stats["trend_score"] = (
            0.35 * topic_stats["volume_norm"]
            + 0.30 * topic_stats["engagement_norm"]
            + 0.35 * topic_stats["momentum_norm"]
        )

        return topic_stats.sort_values("trend_score", ascending=False).reset_index(
            drop=True
        )
