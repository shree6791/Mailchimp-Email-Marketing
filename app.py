"""FastAPI entry: mounts trend and campaign routers. Run ``python app.py`` or ``uvicorn app:app``."""

from __future__ import annotations

from fastapi import FastAPI

from src.api.campaigns import router as campaigns_router
from src.api.trends import router as trends_router
from src.schemas.http_models import HealthResponse

app = FastAPI(
    title="Mailchimp Trend Engine API (stub)",
    description="Reads ``topic_insights.csv`` from Settings.output_dir. Run ``python main.py`` first.",
    version="0.1.0",
)

app.include_router(trends_router)
app.include_router(campaigns_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
