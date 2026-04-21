"""Vision: ingestion layer — fetch and normalize external trending video rows (Kaggle today; APIs/crawl later)."""

from pathlib import Path
import shutil

import kagglehub
import pandas as pd

from src.config.settings import Settings
from src.utils.trending_dates import parse_trending_date_series


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

        df["_td"] = parse_trending_date_series(df["trending_date"])

        n_days = self.settings.recent_trending_days
        if n_days is not None and int(n_days) > 0:
            max_d = df["_td"].max()
            if pd.isna(max_d):
                print("Warning: could not parse trending_date; skipping recent_trending_days filter.")
            else:
                max_norm = pd.Timestamp(max_d).normalize()
                start = max_norm - pd.Timedelta(days=int(n_days) - 1)
                before = len(df)
                df = df.loc[df["_td"] >= start].copy()
                if df.empty:
                    raise ValueError(
                        f"recent_trending_days={int(n_days)} left zero rows after filter. "
                        "Increase the window or set recent_trending_days=None to disable."
                    )
                print(
                    f"recent_trending_days={int(n_days)}: kept {len(df)} rows "
                    f"(trending_date {start.date()} … {max_norm.date()}, was {before})."
                )

        df = df.sort_values("_td", ascending=False, na_position="last")

        if self.settings.max_rows and len(df) > self.settings.max_rows:
            before_cap = len(df)
            df = df.head(self.settings.max_rows).copy()
            print(
                f"max_rows={self.settings.max_rows}: using {len(df)} newest-by-trending_date rows "
                f"(was {before_cap})."
            )

        df = df.drop(columns=["_td"])

        keep = list(required_columns)
        if self.settings.use_description and "description" in df.columns:
            keep.append("description")

        return df[keep].copy()
