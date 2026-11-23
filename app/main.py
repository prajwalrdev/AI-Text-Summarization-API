"""
Main FastAPI Application Entry Point.
"""

from contextlib import asynccontextmanager
from typing import List
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
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
    """
    try:
        Base.metadata.create_all(bind=engine)
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


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    """
    Simple, user-friendly interactive web interface for non-technical users.
    Allows entering custom text and receiving summaries directly in the browser.
    """
    return HTMLResponse(
        content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Text Summarizer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f4f6f9; color: #2d3748; padding: 30px 15px; }
        .container { max-width: 800px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); padding: 35px; }
        h1 { color: #1a202c; font-size: 26px; margin-bottom: 8px; }
        p.subtitle { color: #718096; margin-bottom: 25px; font-size: 14px; }
        label { display: block; font-weight: 600; margin-bottom: 8px; color: #4a5568; }
        textarea { width: 100%; height: 160px; padding: 12px; font-size: 15px; border: 2px solid #e2e8f0; border-radius: 8px; outline: none; transition: border-color 0.2s; resize: vertical; }
        textarea:focus { border-color: #3182ce; }
        .btn-row { display: flex; gap: 10px; margin-top: 15px; }
        button { background: #3182ce; color: #fff; border: none; padding: 12px 24px; font-size: 15px; font-weight: 600; border-radius: 8px; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #2b6cb0; }
        button:disabled { background: #a0aec0; cursor: not-allowed; }
        .docs-link { display: inline-block; margin-left: auto; align-self: center; color: #3182ce; text-decoration: none; font-size: 14px; }
        .result-box { margin-top: 25px; padding: 20px; background: #edf2f7; border-left: 4px solid #3182ce; border-radius: 8px; display: none; }
        .result-box h3 { font-size: 16px; margin-bottom: 8px; color: #2b6cb0; }
        .result-text { font-size: 15px; line-height: 1.6; color: #1a202c; }
        .error-box { margin-top: 25px; padding: 15px; background: #fed7d7; border-left: 4px solid #e53e3e; border-radius: 8px; color: #9b2c2c; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Text Summarizer</h1>
        <p class="subtitle">Powered by FastAPI, Google Gemini, and PostgreSQL</p>
        
        <label for="inputText">Enter your text to summarize:</label>
        <textarea id="inputText" placeholder="Paste or type any long article, news, or notes here..."></textarea>
        
        <div class="btn-row">
            <button id="submitBtn" onclick="generateSummary()">Generate Summary</button>
            <a href="/docs" class="docs-link" target="_blank">Open Swagger API Docs &rarr;</a>
        </div>
        
        <div id="errorBox" class="error-box"></div>
        
        <div id="resultBox" class="result-box">
            <h3>AI Summary</h3>
            <div id="resultText" class="result-text"></div>
        </div>
    </div>

    <script>
        async function generateSummary() {
            const text = document.getElementById('inputText').value.trim();
            const btn = document.getElementById('submitBtn');
            const resultBox = document.getElementById('resultBox');
            const resultText = document.getElementById('resultText');
            const errorBox = document.getElementById('errorBox');

            resultBox.style.display = 'none';
            errorBox.style.display = 'none';

            if (!text) {
                errorBox.innerText = 'Please enter some text before clicking Generate Summary.';
                errorBox.style.display = 'block';
                return;
            }

            btn.disabled = true;
            btn.innerText = 'Generating with Gemini AI...';

            try {
                const response = await fetch('/summarize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || (data.detail && data.detail[0] && data.detail[0].msg) || 'Failed to generate summary.');
                }

                resultText.innerText = data.summary;
                resultBox.style.display = 'block';
            } catch (err) {
                errorBox.innerText = 'Error: ' + err.message;
                errorBox.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.innerText = 'Generate Summary';
            }
        }
    </script>
</body>
</html>
"""
    )
