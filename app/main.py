"""
Main FastAPI Application Entry Point.
"""

from fastapi import FastAPI, status
from app.schemas import HealthResponse, SummarizeRequest, SummarizeResponse

app = FastAPI(
    title="AI Text Summarizer API",
    description="A production-ready REST API for text summarization using FastAPI, Google Gemini, and PostgreSQL.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


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


@app.post(
    "/summarize",
    response_model=SummarizeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Summarization"],
    summary="Generate text summary",
    description="Accepts text in JSON format, validates input via Pydantic, and returns a summary.",
)
def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """
    Summarize input text endpoint.
    
    Validates input using SummarizeRequest schema.
    In Module 4, this calls the Google Gemini API.
    In Module 5, it saves the input and summary to PostgreSQL.
    """
    placeholder_summary = (
        f"Summary: {request.text[:100]}..."
        if len(request.text) > 100
        else f"Summary: {request.text}"
    )
    return SummarizeResponse(summary=placeholder_summary)
