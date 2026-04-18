"""
ML processing layer (vision analog).

Maps to deck **ML Processing**: content prep, NLP (spaCy + embeddings + BERTopic),
trend aggregation/scoring, and LLM insight generation (``src.insights``).

There is **no message queue** in the MVP; calls are in-process inside ``TrendPipelineEngine``.
"""
