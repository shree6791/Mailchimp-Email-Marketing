## Mailchimp Trend Engine

### Overview

This repository provides a batch data pipeline and a Streamlit dashboard. The pipeline ingests regional YouTube trending metadata, clusters videos with BERTopic, assigns a heuristic trend score per topic, and runs offline ranking diagnostics (proxy NDCG, keyword-set diversity) as part of the standard flow before LLM calls. When credentials and configuration allow, it generates topic summaries and structured email campaign copy for a bounded set of top-scoring topics via the OpenAI API.

| Document | Contents |
|----------|-----------|
| [docs/architecture.md](docs/architecture.md) | Runtime architecture, module boundaries, data flow, persisted artifacts, schema references |
| [docs/ml_guide.md](docs/ml_guide.md) | Conceptual walkthrough of ML stages with a small worked example |
| [notebooks/trend_pipeline_walkthrough.ipynb](notebooks/trend_pipeline_walkthrough.ipynb) | Stepwise execution of `DEFAULT_TREND_PIPELINE_STEPS`, then the same top-trends loop as `main.py` |

Metric implementations live in `src/evaluation/` (core functions, console reporting, and `python -m src.evaluation` for CSV replay). Further detail: [Offline ranking evaluation](#offline-ranking-evaluation) below and the architecture document.

### Prerequisites

- Python 3.10 or newer (recommended).
- Network access for dataset download and for OpenAI API calls when insight generation is enabled.

### Installation

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Configuration

Create a `.env` file in the repository root if you use OpenAI-backed insights:

```bash
OPENAI_API_KEY=<secret>
```

Pipeline behavior is controlled by the `Settings` dataclass in [`src/config/settings.py`](src/config/settings.py) (dataset paths, row limits, model names, `log_ranking_evaluation`, and related options).

### Execution

Run the full pipeline from the repository root:

```bash
python main.py
```

This runs the default step sequence, writes CSV artifacts under `data/processed/` and `outputs/`, and prints a short run summary to standard output.

After `outputs/topic_insights.csv` exists, launch the dashboard:

```bash
streamlit run app.py
```

The process binds to the host and port shown in the terminal; browser behavior depends on your environment.

### Data source

By default, the loader retrieves the public Kaggle dataset `datasnaek/youtube-new` (file `USvideos.csv`) via `kagglehub`. Implementation: [`src/ingestion/trending_dataset_loader.py`](src/ingestion/trending_dataset_loader.py).

### Offline ranking evaluation

The default dataset does not include human relevance judgments. During pipeline Step 7 (immediately after trend scoring, before topic-keyword attachment and before any LLM requests), the run prints:

- Proxy NDCG@K (where K equals `llm_top_n`): compares ordering by `trend_score` to an ideal ordering by a proxy gain column (default `volume`).

This block is part of the standard demo (`log_ranking_evaluation` defaults to `True` on `Settings`). Set `log_ranking_evaluation=False` to skip it (for example in headless automation).

To recompute metrics from an exported file:

```bash
python -m src.evaluation outputs/topic_insights.csv
```

### Limitations

- Model and LLM outputs depend on input data, sampling, and prompt design; they are not validated against external policies or ground-truth business metrics.
- This repository does not integrate with Mailchimp or other ESP APIs; it produces local artifacts and UI output only.
