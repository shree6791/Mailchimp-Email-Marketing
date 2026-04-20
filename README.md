## Mailchimp Trend Engine

End-to-end **batch pipeline** plus a **Streamlit** dashboard. It loads public YouTube trending data, clusters videos with BERTopic, ranks trends with a LambdaMART-based scoring pipeline, reports proxy NDCG for ranking quality checks, and generates AI summaries/campaign copy for top rows that pass coherence and marketing-safety checks.

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

### Virtual environment (recommended)

Create and activate a venv **from the repository root** so `pip` and `python` install into that environment (not the system Python).

```bash
cd /path/to/Mailchimp-Email-Marketing
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your shell prompt. If the folder were named `venv` instead, use `source venv/bin/activate` (same pattern).

**Windows (Command Prompt):** `.\.venv\Scripts\activate.bat`  
**Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`

Deactivate later with `deactivate`.

### Install

With the venv **activated**:

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Configuration

- **OpenAI:** create `.env` in the repo root with `OPENAI_API_KEY=<secret>` if you want LLM-generated insights.
- **Pipeline:** edit [`src/config/settings.py`](src/config/settings.py) (`Settings`) for paths, row limits, models, LambdaMART knobs (`lambdamart_*`), `log_ranking_evaluation`, `llm_top_n`, etc.

### Run

From the repository root, with the venv activated (`source .venv/bin/activate`):

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

Offline proxy NDCG lives in [`src/evaluation/`](src/evaluation/) and uses blended gain (`0.5*ctr_recency_norm + 0.3*volume_norm + 0.2*momentum_norm`) against `trend_score`; behavior and interpretation are documented in [`docs/architecture.md`](docs/architecture.md). Recompute from an export:

```bash
python -m src.evaluation outputs/topic_insights.csv
```

### Limitations

- ML and LLM outputs depend on data and configuration; they do not replace policy review or controlled experiments.
- No ESP integration—local artifacts and UI only.
