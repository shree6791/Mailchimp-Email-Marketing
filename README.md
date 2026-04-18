## Mailchimp Trend Engine

End-to-end **batch pipeline** plus a **Streamlit** dashboard. It loads public YouTube trending data, clusters videos with BERTopic, scores topics heuristically, optionally logs **proxy NDCG** (no human labels), then—when configured—calls OpenAI for summaries and campaign copy on the top topics.

This repo does **not** connect to Mailchimp or other ESP APIs; it writes local CSVs and serves a local UI.

| Resource | Purpose |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | Modules, data flow, artifacts, schemas |
| [docs/ml_guide.md](docs/ml_guide.md) | Short narrative walkthrough of ML stages |
| [notebooks/trend_pipeline_walkthrough.ipynb](notebooks/trend_pipeline_walkthrough.ipynb) | Same pipeline steps as `main.py`, in cells |

Offline metrics: [`src/evaluation/`](src/evaluation/) and `python -m src.evaluation` on a saved `topic_insights.csv` (see **Evaluation** below).

### Prerequisites

- Python 3.10+
- Network for dataset download and (if used) OpenAI calls

### Install

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Configuration

- **OpenAI:** create `.env` in the repo root with `OPENAI_API_KEY=<secret>` if you want LLM-generated insights.
- **Pipeline:** edit [`src/config/settings.py`](src/config/settings.py) (`Settings`) for paths, row limits, models, `log_ranking_evaluation`, `llm_top_n`, etc.

### Run

From the repository root:

```bash
python main.py
```

Writes under `data/processed/` and `outputs/` and prints a short summary.

**Dashboard** (after `outputs/topic_insights.csv` exists):

```bash
streamlit run app.py
```

### Data source

Default loader uses the Kaggle dataset `datasnaek/youtube-new` (`USvideos.csv`) via `kagglehub`. See [`src/ingestion/trending_dataset_loader.py`](src/ingestion/trending_dataset_loader.py).

### Evaluation

Offline proxy NDCG lives in [`src/evaluation/`](src/evaluation/); behavior and interpretation are documented in [`docs/architecture.md`](docs/architecture.md). Recompute from an export:

```bash
python -m src.evaluation outputs/topic_insights.csv
```

### Limitations

- ML and LLM outputs depend on data and configuration; they do not replace policy review or controlled experiments.
- No ESP integration—local artifacts and UI only.
