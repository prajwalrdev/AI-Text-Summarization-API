"""
Main FastAPI Application Entry Point.
"""

from fastapi import FastAPI, status
from app.schemas import HealthResponse, SummarizeRequest, SummarizeResponse
from app.services import summarize_text

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
    description="Accepts text in JSON format, validates input via Pydantic, and returns an AI-generated summary from Gemini.",
)
def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """
    Summarize input text using Google's hosted Gemini API.
    
    1. Validates input schema via Pydantic.
    2. Sends text to Gemini via the official google-genai SDK.
    3. Returns the structured AI summary.
    (PostgreSQL persistence is integrated in Module 5).
    """
    summary = summarize_text(request.text)
    return SummarizeResponse(summary=summary)
