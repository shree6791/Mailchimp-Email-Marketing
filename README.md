## Mailchimp Trend Engine

End-to-end **batch pipeline** plus a **Streamlit** dashboard. It loads public YouTube trending data, clusters videos with BERTopic, ranks trends with a LambdaMART-based scoring pipeline, reports proxy NDCG for ranking quality checks, and generates AI summaries/campaign copy for top rows that pass coherence and marketing-safety checks.

This repo does **not** connect to Mailchimp or other ESP APIs; it writes local CSVs and serves a local UI.

**`topic_insights.csv` rows** are a **snapshot for the latest `trending_date` present in the run** (the model scores topic×`ranking_segment` pairs that appear on that day). Row count follows the data, not a fixed cap. Each row includes **`trending_snapshot_date`** (`YYYY-MM-DD`) so exports and APIs know which day the scores target.

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
- **Dashboard data source:** by default [`dashboard.py`](dashboard.py) reads **`outputs/topic_insights.csv`** directly (simple local demo). For a **production-style** setup, run the Trend API and point the UI at it:
  - `export TREND_API_BASE_URL=http://127.0.0.1:8000` (then `streamlit run dashboard.py`). The dashboard loads full rows from `GET /topic-insights/records` on that server. Unset the variable to use the CSV again.
  - Do **not** name the Streamlit file `streamlit.py` — it would shadow the Streamlit package.

### Run

From the repository root, with the venv activated (`source .venv/bin/activate`):

```bash
python main.py
```

Writes under `data/processed/` and `outputs/` and prints a short summary.

**Dashboard** (after `outputs/topic_insights.csv` exists, or API is up):

```bash
streamlit run dashboard.py
```

**HTTP API** ([`app.py`](app.py) mounts [`src/api/trends.py`](src/api/trends.py) and [`src/api/campaigns.py`](src/api/campaigns.py); reads `topic_insights.csv` from `Settings.output_dir`):

```bash
python app.py
```

Same as: `uvicorn app:app --reload --host 127.0.0.1 --port 8000` from repo root with `PYTHONPATH` set to the repo (or run from the repo root so `app` resolves).

- `GET /health` — liveness
- `GET /topic-insights/records` — full table JSON for the Streamlit dashboard (when `TREND_API_BASE_URL` is set)
- `GET /trends?limit=&offset=` — slim list (`trend_id` is `topic:ranking_segment`)
- `GET /trends/{trend_id}` — detail
- `POST /campaigns/{campaign_id}/trends` — body `{"trend_id":"..."}` (in-memory stub, no DB)

More detail: [`docs/api.md`](docs/api.md).

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
