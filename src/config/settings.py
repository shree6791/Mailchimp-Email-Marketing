from dataclasses import dataclass


@dataclass
class Settings:
    dataset_name: str = "datasnaek/youtube-new"
    dataset_region_file: str = "USvideos.csv"

    raw_data_dir: str = "data/raw"
    processed_data_dir: str = "data/processed"
    output_dir: str = "outputs"

    max_rows: int = 5000
    # Keep rows whose trending_date falls in the last N calendar days (relative to max date in CSV).
    # None disables the filter (use full history). Demo default aligns with a ~1-week trending window.
    recent_trending_days: int | None = 7
    # Hours in exp(-age_hours / half_life) for proxy CTR×recency; tune with recent_trending_days if needed.
    recency_half_life_hours: float = 96.0
    use_description: bool = False

    spacy_model_name: str = "en_core_web_sm"
    embedding_model_name: str = "all-MiniLM-L6-v2"

    min_topic_size: int = 15
    stop_words_language: str = "english"

    top_n_topics_to_show: int = 5
    llm_top_n: int = 10
    # Standard demo: proxy NDCG@K (K = llm_top_n) after ranking, before LLM. False skips the block.
    log_ranking_evaluation: bool = True
    llm_model_name: str = "gpt-4.1-mini"

    # LambdaMART ranker (non-personalized LTR) tuned for stable demo behavior.
    lambdamart_n_estimators: int = 160
    lambdamart_learning_rate: float = 0.06
    lambdamart_num_leaves: int = 31
    lambdamart_random_state: int = 42
    lambdamart_min_topic_docs: int = 2
    # Blend learned score with heuristic to keep output stable on small data slices.
    lambdamart_blend_alpha: float = 0.15
