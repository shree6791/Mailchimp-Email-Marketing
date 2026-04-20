"""Vision: ingestion layer — fetch and normalize external trending video rows (Kaggle today; APIs/crawl later)."""

from pathlib import Path
import shutil

import kagglehub
import pandas as pd

from src.config.settings import Settings


class TrendingDatasetLoader:
    """Loads a regional trending CSV from the configured Kaggle bundle into ``data/raw``."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def resolve_dataset_path(self) -> Path:
        dataset_root = Path(kagglehub.dataset_download(self.settings.dataset_name))
        source_csv = dataset_root / self.settings.dataset_region_file

        target_path = Path(self.settings.raw_data_dir) / self.settings.dataset_region_file
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if not target_path.exists():
            print(f"Copying dataset to {target_path}")
            shutil.copy(source_csv, target_path)

        return target_path

    def load(self) -> pd.DataFrame:
        csv_path = self.resolve_dataset_path()
        print(f"Loading dataset from: {csv_path}")

        df = pd.read_csv(csv_path)
        df.columns = [col.strip() for col in df.columns]

        required_columns = [
            "title",
            "tags",
            "views",
            "likes",
            "dislikes",
            "comment_count",
            "trending_date",
            "publish_time",
        ]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if self.settings.use_description and "description" not in df.columns:
            print("Warning: description column missing. Continuing without description.")
            self.settings.use_description = False

        if self.settings.max_rows and len(df) > self.settings.max_rows:
            df = df.head(self.settings.max_rows).copy()

        keep = list(required_columns)
        if self.settings.use_description and "description" in df.columns:
            keep.append("description")

        return df[keep].copy()
