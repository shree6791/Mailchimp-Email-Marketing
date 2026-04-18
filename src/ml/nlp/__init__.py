"""NLP: text normalization, embeddings inputs, and BERTopic clustering (vision: NLP trend extractor core)."""

from src.ml.nlp.spacy_preprocessor import SpacyPreprocessor
from src.ml.nlp.topic_modeler import TopicModeler
from src.ml.nlp.topic_namer import TopicNamer

__all__ = ["SpacyPreprocessor", "TopicModeler", "TopicNamer"]
