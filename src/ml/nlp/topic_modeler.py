import numpy as np
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer

from src.config.settings import Settings
from src.constants.topic_modeling import WEAK_TOPIC_KEYWORDS


class TopicModeler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.topic_model = BERTopic(
            embedding_model=None,
            vectorizer_model=CountVectorizer(
                stop_words=self.settings.stop_words_language
            ),
            min_topic_size=self.settings.min_topic_size,
            calculate_probabilities=True,
            verbose=True,
        )

    def fit_transform(
        self,
        cleaned_texts: list[str],
        embeddings: np.ndarray,
    ) -> tuple[list[int], np.ndarray | None]:
        topics, probs = self.topic_model.fit_transform(cleaned_texts, embeddings)
        return topics, probs

    @staticmethod
    def _is_weak_keyword(token: str) -> bool:
        token = str(token).strip().lower()
        if not token or token.isdigit() or len(token) <= 2:
            return True
        return token in WEAK_TOPIC_KEYWORDS

    def get_topic_keywords(self, topic_id: int, top_n: int = 8) -> list[str]:
        """
        Return the top keywords for a topic, lightly cleaned for display/debugging.
        """
        words = self.topic_model.get_topic(topic_id)
        if not words:
            return []

        keywords: list[str] = []
        for word, _ in words:
            token = str(word).strip().lower()
            if not token:
                continue
            if token.isdigit():
                continue
            if len(token) <= 2:
                continue

            keywords.append(word)
            if len(keywords) >= top_n:
                break

        return keywords

    def get_dominant_topic_keywords(
        self,
        topic_id: int,
        top_n: int = 5,
    ) -> list[str]:
        """
        Return the strongest topic keywords after filtering weaker/generic tail terms.
        This version is intended for LLM input and higher-trust downstream logic.
        """
        words = self.topic_model.get_topic(topic_id)
        if not words:
            return []

        dominant: list[str] = []
        for word, _ in words:
            token = str(word).strip().lower()
            if self._is_weak_keyword(token):
                continue

            dominant.append(word)
            if len(dominant) >= top_n:
                break

        # Fallback: if filtering became too aggressive, fall back to lightly cleaned keywords
        if len(dominant) < 2:
            return self.get_topic_keywords(topic_id, top_n=top_n)

        return dominant
