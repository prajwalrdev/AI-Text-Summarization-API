"""
Service layer for integrating Google Gemini API using the official google-genai SDK.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import HTTPException, status
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError
import httpx

# Always load .env from the project root directory regardless of current working directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Default configuration constants
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
REQUEST_TIMEOUT_SECONDS = 30.0

SUMMARIZATION_SYSTEM_INSTRUCTION = (
    "You are an expert executive summarizer. Analyze the input text carefully and produce a concise, "
    "accurate, and coherent summary capturing the core ideas, primary insights, and essential takeaways. "
    "Maintain an objective tone. Do not include meta-commentary, introductory filler (such as 'Here is a summary:'), "
    "or conversational fluff. Return strictly the summary text."
)


def get_gemini_client() -> genai.Client:
    """
    Instantiate and return the official Google GenAI client.
    Reads the GEMINI_API_KEY from environment variables.
    
    Raises:
        HTTPException: If GEMINI_API_KEY is missing or unconfigured.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() in ("", "your_gemini_api_key_here"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "GEMINI_API_KEY is not configured. Please set a valid Gemini API key in your .env file."
            ),
        )

    # Initialize client with configured timeout
    return genai.Client(
        api_key=api_key.strip(),
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_SECONDS),
    )


def summarize_text(
    text: str,
    client: Optional[genai.Client] = None,
    model: Optional[str] = None,
) -> str:
    """
    Send text to Google's hosted Gemini API and return the generated summary.

    Args:
        text: The validated input text to summarize.
        client: Optional pre-configured GenAI client (enables mocking in automated tests).
        model: Optional model name override (defaults to GEMINI_MODEL env var or gemini-2.5-flash).

    Returns:
        str: The AI-generated summary text.

    Raises:
        HTTPException: Mapped HTTP exceptions for timeouts, rate limits, authentication, or upstream failures.
    """
    if client is None:
        client = get_gemini_client()

    selected_model = model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    prompt = (
        f"Please summarize the following text concisely while preserving all critical information:\n\n{text}"
    )

    config = types.GenerateContentConfig(
        system_instruction=SUMMARIZATION_SYSTEM_INSTRUCTION,
        temperature=0.2,  # Low temperature for factual, deterministic summaries
        max_output_tokens=1024,
    )

    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=config,
        )

        if not response or not response.text:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini API returned an empty or invalid response.",
            )

        return response.text.strip()

    except (TimeoutError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"The request to Google Gemini API timed out after {REQUEST_TIMEOUT_SECONDS} seconds.",
        ) from exc

    except ClientError as exc:
        # Client-side API errors (e.g., 400 Bad Request, 401/403 Invalid API Key, 429 Rate Limit)
        status_code = getattr(exc, "code", 400)
        if status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Gemini API quota or rate limit exceeded. Please try again later.",
            ) from exc
        if status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini API authentication failed. Verify your GEMINI_API_KEY.",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API client error: {exc.message if hasattr(exc, 'message') else str(exc)}",
        ) from exc

    except (ServerError, APIError) as exc:
        # Upstream Google server errors (5xx)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Gemini upstream service error: {exc.message if hasattr(exc, 'message') else str(exc)}",
        ) from exc

    except HTTPException:
        # Re-raise already formed HTTPExceptions
        raise

    except Exception as exc:
        # Generic fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while communicating with Gemini API: {str(exc)}",
        ) from exc
