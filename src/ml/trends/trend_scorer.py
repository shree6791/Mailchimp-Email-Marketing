import re
from typing import Mapping

from lightgbm import LGBMRanker
import numpy as np
import pandas as pd

from src.config.settings import Settings
from src.ml.trends.trend_taxonomy import classify_trend_type
from src.utils.text_utils import safe_text


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

    @staticmethod
    def _minmax_by_group(
        frame: pd.DataFrame, value_col: str, group_cols: list[str]
    ) -> pd.Series:
        grouped = frame.groupby(group_cols)[value_col]
        mins = grouped.transform("min")
        maxs = grouped.transform("max")
        denom = (maxs - mins).replace(0, np.nan)
        out = (frame[value_col] - mins) / (denom + 1e-12)
        return out.fillna(0.0).clip(0.0, 1.0)

    def _attach_video_segments(
        self,
        valid: pd.DataFrame,
        topic_modeler: object,
        dominant_keywords_by_topic: Mapping[int, list[str]] | None = None,
    ) -> pd.DataFrame:
        """
        Assign segment at video-row level so a topic can appear in multiple segments.
        """
        out = valid.copy()
        if dominant_keywords_by_topic is None:
            topic_ids = out["topic"].dropna().astype(int).unique().tolist()
            topic_keywords = {
                topic_id: topic_modeler.get_dominant_topic_keywords(topic_id)
                for topic_id in topic_ids
            }
        else:
            topic_keywords = {
                int(topic_id): keywords
                for topic_id, keywords in dominant_keywords_by_topic.items()
            }

        def _segment_for_row(row: pd.Series) -> str:
            topic_id = int(row["topic"])
            keywords = topic_keywords.get(topic_id, [])
            title = safe_text(row.get("title", ""))
            return classify_trend_type(keywords, [title])

        out["ranking_segment"] = out.apply(_segment_for_row, axis=1)
        out["ranking_segment"] = out["ranking_segment"].fillna("general")
        return out

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

    def _apply_segment_global_merge(
        self,
        ranked_topics: pd.DataFrame,
        base_score_col: str = "trend_score",
    ) -> pd.DataFrame:
        """
        Build a single global ordering from segment-local rankings.
        This keeps one leaderboard output while enforcing segment-first coverage.
        """
        out = ranked_topics.copy()
        if out.empty or "ranking_segment" not in out.columns:
            return out

        if out["ranking_segment"].nunique(dropna=False) <= 1:
            return out.sort_values(base_score_col, ascending=False).reset_index(drop=True)

        out["segment_rank"] = out.groupby("ranking_segment")[base_score_col].rank(
            method="first",
            ascending=False,
        )
        max_rank = max(float(out["segment_rank"].max()), 1.0)
        out["segment_round_score"] = (
            1.0 - ((out["segment_rank"] - 1.0) / max_rank)
        ).clip(lower=0.0, upper=1.0)

        out["global_score_norm"] = self.normalize_series(out[base_score_col])
        out["trend_score"] = (
            0.7 * out["segment_round_score"] + 0.3 * out["global_score_norm"]
        )
        return out.sort_values("trend_score", ascending=False).reset_index(drop=True)

    def _build_lambdamart_training_frame(self, valid: pd.DataFrame) -> pd.DataFrame:
        """Build per-date+segment topic rows with blended CTR+momentum relevance."""
        daily_topic = (
            valid.groupby(["date", "ranking_segment", "topic"])
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
            .sort_values(["ranking_segment", "topic", "date"])
        )
        if daily_topic.empty:
            return daily_topic

        daily_topic = daily_topic[
            daily_topic["doc_count"] >= self.settings.lambdamart_min_topic_docs
        ].copy()
        if daily_topic.empty:
            return daily_topic

        daily_topic["prev_doc_count"] = (
            daily_topic.groupby(["ranking_segment", "topic"])["doc_count"]
            .shift(1)
            .fillna(0.0)
        )
        daily_topic["momentum"] = (
            (daily_topic["doc_count"] - daily_topic["prev_doc_count"])
            / (daily_topic["prev_doc_count"] + 1.0)
        )

        query_cols = ["date", "ranking_segment"]
        daily_topic["ctr_recency_norm_q"] = self._minmax_by_group(
            daily_topic,
            "avg_proxy_ctr_recency",
            query_cols,
        )
        daily_topic["momentum_norm_q"] = self._minmax_by_group(
            daily_topic,
            "momentum",
            query_cols,
        )
        daily_topic["label_gain"] = (
            0.7 * daily_topic["ctr_recency_norm_q"]
            + 0.3 * daily_topic["momentum_norm_q"]
        )

        pct = daily_topic.groupby(query_cols)["label_gain"].rank(method="average", pct=True)
        daily_topic["label_relevance"] = pd.cut(
            pct,
            bins=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            labels=[0, 1, 2, 3, 4],
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

        train_df = self._build_lambdamart_training_frame(valid)
        if train_df.empty:
            raise RuntimeError(
                "LambdaMART training frame is empty after segment/date preparation."
            )

        train_df = train_df.sort_values(["date", "ranking_segment", "topic"]).reset_index(drop=True)
        query_sizes = train_df.groupby(["date", "ranking_segment"]).size()
        query_sizes = query_sizes[query_sizes > 1]
        if len(query_sizes) < 3 or int(query_sizes.sum()) < 25:
            raise RuntimeError(
                "LambdaMART training requires at least 3 multi-topic (date, segment) queries and 25 rows."
            )

        valid_queries = query_sizes.index.to_frame(index=False)
        train_df = train_df.merge(valid_queries, on=["date", "ranking_segment"], how="inner")
        train_df["segment_code"] = train_df["ranking_segment"].astype("category").cat.codes

        feature_cols = [
            "segment_code",
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
        group = train_df.groupby(["date", "ranking_segment"]).size().tolist()

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

        segment_map = (
            train_df[["ranking_segment", "segment_code"]]
            .drop_duplicates()
            .set_index("ranking_segment")["segment_code"]
            .to_dict()
        )
        pred_df = (
            valid[valid["date"] == latest_date]
            .groupby(["ranking_segment", "topic"])
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
            raise RuntimeError(
                "LambdaMART prediction frame is empty for the latest ranking date."
            )

        pred_df["segment_code"] = (
            pred_df["ranking_segment"].map(segment_map).fillna(-1).astype(int)
        )
        pred_df["lambdamart_score_raw"] = model.predict(pred_df[feature_cols])
        pred_df["lambdamart_score_norm"] = self.normalize_series(pred_df["lambdamart_score_raw"])

        # Expand topic-level anchors into topic+segment rows seen at prediction time.
        out = pred_df[["topic", "ranking_segment"]].drop_duplicates().merge(
            out,
            on="topic",
            how="left",
        )
        if out.empty:
            raise RuntimeError(
                "No overlapping topic/segment rows between topic stats and LambdaMART predictions."
            )

        out = out.merge(
            pred_df[
                [
                    "topic",
                    "ranking_segment",
                    "lambdamart_score_raw",
                    "lambdamart_score_norm",
                ]
            ],
            on=["topic", "ranking_segment"],
            how="left",
        )
        if out["lambdamart_score_norm"].isna().any() or out["lambdamart_score_raw"].isna().any():
            raise RuntimeError(
                "LambdaMART predictions are missing for one or more topic/segment rows."
            )

        # Keep ranking behavior stable by blending learned and anchor signals.
        out["trend_score"] = (
            self.settings.lambdamart_blend_alpha * out["lambdamart_score_norm"]
            + (1.0 - self.settings.lambdamart_blend_alpha) * out["anchor_score"]
        )
        return self._apply_segment_global_merge(out, base_score_col="trend_score")

    def score(
        self,
        videos_df: pd.DataFrame,
        topic_modeler: object,
        dominant_keywords_by_topic: Mapping[int, list[str]] | None = None,
    ) -> pd.DataFrame:
        valid = videos_df[videos_df["topic"] != -1].copy()
        if valid.empty:
            return pd.DataFrame()

        valid["date"] = self.parse_trending_date(valid["trending_date"])
        valid = valid.dropna(subset=["date"])
        if valid.empty:
            return pd.DataFrame()
        valid = self._build_video_level_features(valid)
        valid = self._attach_video_segments(
            valid,
            topic_modeler,
            dominant_keywords_by_topic=dominant_keywords_by_topic,
        )
        topic_stats, latest_date = self._build_topic_stats(valid)
        topic_stats = self._apply_anchor_score(topic_stats)
        scored = self._apply_lambdamart_score(topic_stats, valid, latest_date)
        if scored.empty:
            return scored
        ts = pd.Timestamp(latest_date)
        scored["trending_snapshot_date"] = ts.strftime("%Y-%m-%d")
        return scored
