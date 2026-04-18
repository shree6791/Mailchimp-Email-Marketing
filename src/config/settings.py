from dataclasses import dataclass


@dataclass
class Settings:
    dataset_name: str = "datasnaek/youtube-new"
    dataset_region_file: str = "USvideos.csv"

    raw_data_dir: str = "data/raw"
    processed_data_dir: str = "data/processed"
    output_dir: str = "outputs"

    max_rows: int = 5000
    use_description: bool = False

    spacy_model_name: str = "en_core_web_sm"
    embedding_model_name: str = "all-MiniLM-L6-v2"

    min_topic_size: int = 15
    stop_words_language: str = "english"

    top_n_topics_to_show: int = 5
    llm_top_n: int = 5
    # Standard demo: proxy NDCG@K (K = llm_top_n) after ranking, before LLM. False skips the block.
    log_ranking_evaluation: bool = True
    llm_model_name: str = "gpt-4.1-mini"