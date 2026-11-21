"""
Main FastAPI Application Entry Point.
"""

from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI(
    title="AI Text Summarizer API",
    description="A production-ready REST API for text summarization using FastAPI, Google Gemini, and PostgreSQL.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Check API health status",
)
def health_check() -> HealthResponse:
    """
    Health check endpoint to verify that the service is running.
    """
    return HealthResponse(status="healthy", version="1.0.0")
