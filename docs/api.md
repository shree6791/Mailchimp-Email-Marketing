# Trend Engine HTTP API

This repository exposes a small **FastAPI** service that reads pipeline output from **`topic_insights.csv`** (no database). It is intended for demos, local development, and the same contract the Streamlit dashboard can use when **`TREND_API_BASE_URL`** is set.

Interactive schema and “try it” UI: **`http://127.0.0.1:8000/docs`** (Swagger UI) and **`/redoc`**.

---

## Running the server

From the **repository root** (so the `app` module resolves):

```bash
python app.py
```

Equivalent:

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Ensure **`PYTHONPATH`** includes the repo root if you invoke Python from elsewhere (VS Code launch configs set this).

---

## Data dependency

- The API loads **`{Settings().output_dir}/topic_insights.csv`** (default **`outputs/topic_insights.csv`**).
- If that file is **missing**, trend endpoints return **503** with a message to run the pipeline (`python main.py`) first.
- If the file exists but has **no data rows**, list and record endpoints return **empty** payloads (not 503).

---

## `trend_id` format

Trends are keyed by a string:

```text
{topic_int}:{ranking_segment}
```

Examples: `5:US`, `12:general`. If `ranking_segment` is missing or blank in the row, the segment is treated as **`default`** when building the id (see `src/api/trends.py`).

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness; body `{ "status": "ok" }`. |
| `GET` | `/topic-insights/records` | Full table: validated **`TopicInsightRow`** objects (best for UIs / parity with CSV). |
| `GET` | `/trends` | Paginated **slim** list (`limit`, `offset`). |
| `GET` | `/trends/{trend_id}` | Single trend **detail** (keywords, campaign copy fields). |
| `POST` | `/campaigns/{campaign_id}/trends` | **Stub**: accepts `{ "trend_id": "..." }`; does **not** persist. |

### Query parameters

- **`GET /trends`**: `limit` (default `20`), `offset` (default `0`).

### Status codes (summary)

| Code | When |
|------|------|
| `200` | Success. |
| `404` | `GET /trends/{trend_id}` — id not found. |
| `503` | `topic_insights.csv` not found on disk. |

---

## JSON shapes and Pydantic models

Response bodies are defined in **`src/schemas/http_models.py`**. Full-row responses reuse the pipeline row model **`TopicInsightRow`** from **`src/schemas/topic_insights.py`** (nested **`EmailCampaignCopy`** for `campaign_copy`).

| Response model | Used for |
|----------------|----------|
| `HealthResponse` | `/health` |
| `TopicInsightsRecordsResponse` | `/topic-insights/records` (`records`, `count`) |
| `TrendListResponse` | `/trends` (`items`, `limit`, `offset`, `total`) |
| `TrendListItem` | Each element of `items` on `/trends` |
| `TrendDetail` | `/trends/{trend_id}` |
| `CampaignTrendLinkResponse` | `POST /campaigns/...` |

Request body for the campaign stub:

| Request model | Used for |
|---------------|----------|
| `CampaignTrendLink` | `POST /campaigns/{campaign_id}/trends` |

Field names and types in OpenAPI match these models (FastAPI `response_model`).

---

## Code layout

| Location | Role |
|----------|------|
| [`app.py`](../app.py) | FastAPI app, `/health`, mounts routers. |
| [`src/api/trends.py`](../src/api/trends.py) | Trend list, detail, full records. |
| [`src/api/campaigns.py`](../src/api/campaigns.py) | Campaign–trend stub. |
| [`src/schemas/http_models.py`](../src/schemas/http_models.py) | HTTP request/response Pydantic models. |

---

## Tests

API behavior is covered in **`tests/test_api_endpoints.py`** using **`TestClient`** (no live server required). Run:

```bash
pytest tests/test_api_endpoints.py -v
```

---

## Related

- Streamlit loads this API when **`TREND_API_BASE_URL`** points at the running service (see `src/serving/streamlit/data_loading.py`).
- Broader system architecture: [`architecture.md`](architecture.md).
