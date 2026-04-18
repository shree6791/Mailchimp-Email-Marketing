"""Ingestion layer: connectors that land normalized rows (vision: crawl + social APIs; MVP: Kaggle trending CSV)."""

from src.ingestion.trending_dataset_loader import TrendingDatasetLoader

__all__ = ["TrendingDatasetLoader"]
