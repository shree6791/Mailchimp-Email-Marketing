import re

import numpy as np
import pandas as pd

from src.config.settings import Settings
from src.utils.text_utils import safe_text

try:
    from lightgbm import LGBMRanker  # type: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - optional dependency
    LGBMRanker = None


class TrendScorer:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()

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

    @staticmethod
    def _build_video_level_features(valid: pd.DataFrame) -> pd.DataFrame:
        """Create robust per-video ranking features from available engagement fields."""
        out = valid.copy()
        out["views_safe"] = out["views"].clip(lower=1)
        out["likes_safe"] = out["likes"].clip(lower=0)
        out["comments_safe"] = out["comment_count"].clip(lower=0)
        out["dislikes_safe"] = out.get("dislikes", pd.Series(0, index=out.index)).clip(lower=0)

        out["engagement"] = (
            np.log1p(out["views_safe"])
            + 0.7 * np.log1p(out["likes_safe"])
            + 0.4 * np.log1p(out["comments_safe"])
        )

        # Proxy CTR-like engagement rate from raw counters (bounded to keep outliers stable).
        out["proxy_ctr"] = (
            (
                out["likes_safe"]
                + 0.5 * out["comments_safe"]
                - 0.25 * out["dislikes_safe"]
            )
            / out["views_safe"]
        ).clip(lower=0.0, upper=1.0)

        publish_series = (
            out["publish_time"]
            if "publish_time" in out.columns
            else pd.Series(pd.NaT, index=out.index)
        )
        publish_time = pd.to_datetime(publish_series, errors="coerce", utc=True)
        if hasattr(publish_time.dt, "tz_convert"):
            publish_time = publish_time.dt.tz_convert(None)
        age_hours = (out["date"] - publish_time).dt.total_seconds() / 3600.0
        out["age_hours"] = age_hours.clip(lower=0).fillna(72.0)

        # Higher weight for fresher videos while keeping older content relevant.
        out["recency_weight"] = np.exp(-out["age_hours"] / 96.0).clip(lower=0.2, upper=1.0)
        out["proxy_ctr_recency"] = (out["proxy_ctr"] * out["recency_weight"]).clip(0.0, 1.0)
        return out

    def _build_topic_stats(
        self, valid: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.Timestamp]:
        daily_counts = valid.groupby(["topic", "date"]).size().reset_index(name="doc_count")

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
                avg_proxy_ctr=("proxy_ctr", "mean"),
                avg_proxy_ctr_recency=("proxy_ctr_recency", "mean"),
                avg_age_hours=("age_hours", "mean"),
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
        topic_stats["freshness"] = 1.0 / (1.0 + topic_stats["avg_age_hours"].clip(lower=0))
        return topic_stats, latest_date

    def _apply_anchor_score(self, topic_stats: pd.DataFrame) -> pd.DataFrame:
        out = topic_stats.copy()
        out["volume_norm"] = self.normalize_series(out["volume"])
        out["engagement_norm"] = self.normalize_series(out["avg_engagement"])
        out["momentum_norm"] = self.normalize_series(out["momentum"])
        out["proxy_ctr_norm"] = self.normalize_series(out["avg_proxy_ctr_recency"])
        out["freshness_norm"] = self.normalize_series(out["freshness"])

        out["anchor_score"] = (
            0.28 * out["volume_norm"]
            + 0.24 * out["engagement_norm"]
            + 0.22 * out["momentum_norm"]
            + 0.18 * out["proxy_ctr_norm"]
            + 0.08 * out["freshness_norm"]
        )
        return out

    def _build_lambdamart_training_frame(self, valid: pd.DataFrame) -> pd.DataFrame:
        """Build per-date topic rows with next-day growth as pseudo relevance label."""
        daily_topic = (
            valid.groupby(["date", "topic"])
            .agg(
                doc_count=("topic", "size"),
                avg_views=("views", "mean"),
                avg_likes=("likes", "mean"),
                avg_comments=("comment_count", "mean"),
                avg_engagement=("engagement", "mean"),
                avg_proxy_ctr=("proxy_ctr", "mean"),
                avg_proxy_ctr_recency=("proxy_ctr_recency", "mean"),
                avg_age_hours=("age_hours", "mean"),
            )
            .reset_index()
            .sort_values(["topic", "date"])
        )
        if daily_topic.empty:
            return daily_topic
        daily_topic = daily_topic[
            daily_topic["doc_count"] >= self.settings.lambdamart_min_topic_docs
        ].copy()
        if daily_topic.empty:
            return daily_topic

        daily_topic["next_doc_count"] = daily_topic.groupby("topic")["doc_count"].shift(-1)
        daily_topic["next_avg_engagement"] = daily_topic.groupby("topic")["avg_engagement"].shift(-1)
        daily_topic = daily_topic.dropna(subset=["next_doc_count", "next_avg_engagement"]).copy()
        if daily_topic.empty:
            return daily_topic

        growth = (daily_topic["next_doc_count"] - daily_topic["doc_count"]) / (
            daily_topic["doc_count"] + 1.0
        )
        future_engagement_lift = (
            daily_topic["next_avg_engagement"] / (daily_topic["avg_engagement"] + 1e-6)
        )
        label = growth + 0.15 * (future_engagement_lift - 1.0)
        daily_topic["label_gain"] = np.clip(label, -1.0, 3.0)
        # LambdaMART in LightGBM expects integer relevance labels.
        # Use coarse per-date buckets to avoid over-reacting to tiny label noise.
        pct = daily_topic.groupby("date")["label_gain"].rank(method="average", pct=True)
        daily_topic["label_relevance"] = pd.cut(
            pct,
            bins=[0.0, 0.33, 0.66, 1.0],
            labels=[0, 1, 2],
            include_lowest=True,
        ).astype(int)
        return daily_topic

    def _apply_lambdamart_score(
        self,
        topic_stats: pd.DataFrame,
        valid: pd.DataFrame,
        latest_date: pd.Timestamp,
    ) -> pd.DataFrame:
        out = topic_stats.copy()
        out["ranker"] = "lambdamart_fallback"

        if LGBMRanker is None:
            print("lightgbm not installed; falling back to anchor-score ranking.")
            out["trend_score"] = out["anchor_score"]
            return out.sort_values("trend_score", ascending=False).reset_index(drop=True)

        train_df = self._build_lambdamart_training_frame(valid)
        if train_df.empty:
            out["trend_score"] = out["anchor_score"]
            return out.sort_values("trend_score", ascending=False).reset_index(drop=True)

        train_df = train_df.sort_values(["date", "topic"]).reset_index(drop=True)
        query_sizes = train_df.groupby("date").size()
        query_sizes = query_sizes[query_sizes > 1]
        if len(query_sizes) < 3 or int(query_sizes.sum()) < 25:
            out["trend_score"] = out["anchor_score"]
            return out.sort_values("trend_score", ascending=False).reset_index(drop=True)

        train_df = train_df[train_df["date"].isin(query_sizes.index)].copy()
        feature_cols = [
            "doc_count",
            "avg_views",
            "avg_likes",
            "avg_comments",
            "avg_engagement",
            "avg_proxy_ctr",
            "avg_proxy_ctr_recency",
            "avg_age_hours",
        ]
        X_train = train_df[feature_cols]
        y_train = train_df["label_relevance"]
        group = train_df.groupby("date").size().tolist()

        model = LGBMRanker(
            objective="lambdarank",
            metric="ndcg",
            n_estimators=self.settings.lambdamart_n_estimators,
            learning_rate=self.settings.lambdamart_learning_rate,
            num_leaves=self.settings.lambdamart_num_leaves,
            min_data_in_leaf=5,
            n_jobs=1,
            random_state=self.settings.lambdamart_random_state,
            verbosity=-1,
        )
        model.fit(X_train, y_train, group=group)

        pred_df = (
            valid[valid["date"] == latest_date]
            .groupby("topic")
            .agg(
                doc_count=("topic", "size"),
                avg_views=("views", "mean"),
                avg_likes=("likes", "mean"),
                avg_comments=("comment_count", "mean"),
                avg_engagement=("engagement", "mean"),
                avg_proxy_ctr=("proxy_ctr", "mean"),
                avg_proxy_ctr_recency=("proxy_ctr_recency", "mean"),
                avg_age_hours=("age_hours", "mean"),
            )
            .reset_index()
        )
        if pred_df.empty:
            out["trend_score"] = out["anchor_score"]
            return out.sort_values("trend_score", ascending=False).reset_index(drop=True)

        pred_df["lambdamart_score_raw"] = model.predict(pred_df[feature_cols])
        pred_df["lambdamart_score_norm"] = self.normalize_series(pred_df["lambdamart_score_raw"])

        out = out.merge(
            pred_df[["topic", "lambdamart_score_raw", "lambdamart_score_norm"]],
            on="topic",
            how="left",
        )
        out["lambdamart_score_norm"] = out["lambdamart_score_norm"].fillna(0.0)
        out["lambdamart_score_raw"] = out["lambdamart_score_raw"].fillna(0.0)

        # Keep ranking behavior stable by blending learned and anchor signals.
        out["trend_score"] = (
            self.settings.lambdamart_blend_alpha * out["lambdamart_score_norm"]
            + (1.0 - self.settings.lambdamart_blend_alpha) * out["anchor_score"]
        )
        out["ranker"] = "lambdamart_blended"
        return out.sort_values("trend_score", ascending=False).reset_index(drop=True)

    def score(self, videos_df: pd.DataFrame) -> pd.DataFrame:
        valid = videos_df[videos_df["topic"] != -1].copy()
        if valid.empty:
            return pd.DataFrame()

        valid["date"] = self.parse_trending_date(valid["trending_date"])
        valid = valid.dropna(subset=["date"])
        if valid.empty:
            return pd.DataFrame()
        valid = self._build_video_level_features(valid)
        topic_stats, latest_date = self._build_topic_stats(valid)
        topic_stats = self._apply_anchor_score(topic_stats)

        return self._apply_lambdamart_score(topic_stats, valid, latest_date)
