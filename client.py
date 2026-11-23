"""
Interactive Terminal Client for AI Text Summarizer.
Allows you to enter your own custom text and see the generated summary immediately.
Works seamlessly whether the FastAPI server is running or offline!
"""

import sys
from pathlib import Path
import requests

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

API_URL = "http://127.0.0.1:8000/summarize"


def summarize_offline(text: str) -> str:
    """
    Direct fallback: Summarizes using Gemini AI service and persists to PostgreSQL
    when the HTTP web server is not running in another terminal.
    """
    from app.services import summarize_text
    from app.database import SessionLocal
    from app.models import Summary

    # 1. Call Gemini AI
    summary = summarize_text(text)

    # 2. Persist to PostgreSQL database
    db = SessionLocal()
    try:
        record = Summary(original_text=text, generated_summary=summary)
        db.add(record)
        db.commit()
        db.refresh(record)
    finally:
        db.close()

    return summary


def main():
    print("\n" + "=" * 60)
    print("        AI TEXT SUMMARIZER - INTERACTIVE CLIENT")
    print("=" * 60)
    print("Type or paste any text to summarize. (Type 'exit' to quit)\n")

    while True:
        try:
            user_text = input("\n👉 Enter your text:\n> ").strip()

            if not user_text:
                print("⚠️  Input cannot be empty. Please type some text.")
                continue

            if user_text.lower() in ("exit", "quit", "q"):
                print("\nGoodbye!\n")
                break

            print("\n⏳ Sending to Gemini AI & saving to PostgreSQL database...")

            # Method 1: Try HTTP API endpoint first
            summary = None
            try:
                response = requests.post(
                    API_URL,
                    json={"text": user_text},
                    headers={"Content-Type": "application/json"},
                    timeout=45,
                )
                if response.status_code == 200:
                    summary = response.json().get("summary")
                else:
                    error_detail = response.json().get("detail", response.text)
                    print(f"\n❌ API Error ({response.status_code}): {error_detail}")
                    continue
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                # Method 2: If server is not running in background, seamlessly process directly!
                summary = summarize_offline(user_text)

            if summary:
                print("\n" + "-" * 60)
                print("✨ AI GENERATED SUMMARY:")
                print("-" * 60)
                print(summary)
                print("-" * 60)
                print("✅ [Saved to PostgreSQL Database successfully]")

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
