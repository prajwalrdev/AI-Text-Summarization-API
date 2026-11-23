"""
Main FastAPI Application Entry Point.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import List
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Summary
from app.schemas import (
    HealthResponse,
    SummarizeRequest,
    SummarizeResponse,
    SummaryRecord,
)
from app.services import summarize_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes database tables on application startup.
    Runs create_all in a worker thread so a slow/unreachable DB cannot block the event loop.
    """
    try:
        await asyncio.to_thread(Base.metadata.create_all, bind=engine)
    except Exception as exc:
        print(f"Notice: Database table initialization deferred or failed: {exc}")
    yield


app = FastAPI(
    title="AI Text Summarizer API",
    description="A production-ready REST API for text summarization using FastAPI, Google Gemini, and PostgreSQL.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """
    Root URL has no API page. Redirect browsers to the interactive Swagger docs.
    """
    return RedirectResponse(url="/docs")


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
    summary="Generate and save text summary",
    description="Accepts text in JSON format, generates summary with Gemini, and saves to the database.",
)
def summarize(
    request: SummarizeRequest,
    db: Session = Depends(get_db),
) -> SummarizeResponse:
    """
    Summarize input text endpoint.
    
    1. Validates input schema via Pydantic.
    2. Sends text to Google's hosted Gemini API.
    3. Persists original text and generated summary in PostgreSQL database.
    4. Returns the AI-generated summary.
    """
    # 1. Call Gemini AI service
    summary = summarize_text(request.text)

    # 2. Persist record into the PostgreSQL database
    try:
        record = Summary(
            original_text=request.text,
            generated_summary=summary,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred while persisting summary: {str(exc)}",
        ) from exc

    return SummarizeResponse(summary=summary)


@app.get(
    "/summaries",
    response_model=List[SummaryRecord],
    status_code=status.HTTP_200_OK,
    tags=["Summarization"],
    summary="List stored summaries",
    description="Retrieve stored summarization records from the database for verification.",
)
def get_summaries(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> List[SummaryRecord]:
    """
    Retrieve stored summary records ordered by creation date and id descending.
    """
    try:
        query = select(Summary).order_by(Summary.created_at.desc(), Summary.id.desc()).limit(limit)
        results = db.scalars(query).all()
        return list(results)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query error: {str(exc)}",
        ) from exc
