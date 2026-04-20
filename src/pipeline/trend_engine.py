import numpy as np
import pandas as pd

from src.config.settings import Settings
from src.ingestion.trending_dataset_loader import TrendingDatasetLoader
from src.insights.insight_generator import InsightGenerator
from src.ml.embeddings.embedding_service import EmbeddingService
from src.ml.nlp.spacy_preprocessor import SpacyPreprocessor
from src.ml.nlp.topic_modeler import TopicModeler
from src.ml.nlp.topic_namer import TopicNamer
from src.evaluation.reporting import log_ranking_evaluation
from src.ml.trends.topic_insight_enrichment import (
    add_topic_keyword_columns,
    enrich_topic_insights_marketer_fields,
)
from src.ml.trends.trend_scorer import TrendScorer
from src.pipeline.pipeline_run import run_trend_pipeline
from src.utils.text_utils import build_document


class TrendPipelineEngine:
    """Orchestrates ingestion → ML → storage steps (vision: batch analog of scheduled pipeline)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.trending_dataset_loader = TrendingDatasetLoader(settings)
        self.preprocessor = SpacyPreprocessor(settings.spacy_model_name)
        self.embedding_service = EmbeddingService(settings.embedding_model_name)
        self.topic_modeler = TopicModeler(settings)
        self.topic_namer = TopicNamer()
        self.trend_scorer = TrendScorer(settings)
        self.insight_generator = InsightGenerator(model=settings.llm_model_name)
        self._topic_keywords_cache: dict[int, list[str]] = {}
        self._dominant_topic_keywords_cache: dict[int, list[str]] = {}

    def _refresh_topic_keyword_cache(self, videos_df: pd.DataFrame) -> None:
        """
        Precompute per-topic keyword lists once for reuse across scoring and enrichment.
        """
        topic_ids = (
            videos_df.loc[videos_df["topic"] != -1, "topic"]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )
        self._topic_keywords_cache = {
            topic_id: self.topic_modeler.get_topic_keywords(topic_id)
            for topic_id in topic_ids
        }
        self._dominant_topic_keywords_cache = {
            topic_id: self.topic_modeler.get_dominant_topic_keywords(topic_id)
            for topic_id in topic_ids
        }

    def prepare_documents(self, videos_df: pd.DataFrame) -> pd.DataFrame:
        videos_df = videos_df.copy()
        videos_df["document"] = videos_df.apply(
            lambda row: build_document(row, self.settings.use_description),
            axis=1,
        )
        return videos_df

    def enrich_documents(self, videos_df: pd.DataFrame) -> pd.DataFrame:
        cleaned_texts = self.preprocessor.transform(videos_df["document"].fillna("").tolist())
        videos_df = videos_df.copy()
        videos_df["cleaned_text"] = cleaned_texts
        return videos_df

    def assign_topics(self, videos_df: pd.DataFrame) -> pd.DataFrame:
        embeddings = self.embedding_service.encode(videos_df["cleaned_text"].tolist())
        topics, probs = self.topic_modeler.fit_transform(
            videos_df["cleaned_text"].tolist(),
            embeddings,
        )

        videos_df = videos_df.copy()
        videos_df["topic"] = topics
        if probs is not None:
            videos_df["topic_confidence"] = [
                float(np.max(prob)) if prob is not None else np.nan
                for prob in probs
            ]
        else:
            videos_df["topic_confidence"] = np.nan
        return videos_df

    def score_topic_aggregates(self, videos_df: pd.DataFrame) -> pd.DataFrame:
        """Per-topic aggregates from ``TrendScorer`` (no keywords or LLM)."""
        self._refresh_topic_keyword_cache(videos_df)
        topic_insights = self.trend_scorer.score(
            videos_df,
            self.topic_modeler,
            dominant_keywords_by_topic=self._dominant_topic_keywords_cache,
        )
        if topic_insights.empty:
            raise RuntimeError(
                "Topic scoring produced no results. Check input data or date parsing."
            )
        return topic_insights

    def attach_topic_keywords(self, topic_insights: pd.DataFrame) -> pd.DataFrame:
        """Add ``topic_keywords`` / labels from the fitted topic model."""
        out = topic_insights.copy()
        add_topic_keyword_columns(
            out,
            self.topic_modeler,
            topic_keywords_by_topic=self._topic_keywords_cache,
            dominant_keywords_by_topic=self._dominant_topic_keywords_cache,
        )
        return out

    def log_topic_ranking_evaluation(self, topic_insights: pd.DataFrame) -> None:
        """Print proxy NDCG when ``log_ranking_evaluation`` is enabled."""
        if not self.settings.log_ranking_evaluation:
            return
        llm_top_n = min(self.settings.llm_top_n, len(topic_insights))
        log_ranking_evaluation(topic_insights, ndcg_k=llm_top_n)

    def enrich_marketer_insights(
        self, videos_df: pd.DataFrame, topic_insights: pd.DataFrame
    ) -> pd.DataFrame:
        """Heuristics + LLM copy (expects topic keywords on ``topic_insights``)."""
        llm_top_n = min(self.settings.llm_top_n, len(topic_insights))
        return enrich_topic_insights_marketer_fields(
            videos_with_topics=videos_df,
            topic_insights=topic_insights,
            topic_namer=self.topic_namer,
            insight_generator=self.insight_generator,
            llm_top_n=llm_top_n,
        )

    def run(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        return run_trend_pipeline(self)
