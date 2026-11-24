"""
Comprehensive System Diagnostic & Debug Script.
Verifies all 6 layers of the AI Text Summarization project:
1. Python environment and libraries
2. Environment variables (.env)
3. PostgreSQL database connectivity & tables
4. Google Gemini hosted cloud AI
5. FastAPI REST endpoints & Pydantic validation
6. Pytest automated test suite
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_diagnostics():
    print("=" * 70)
    print("         AI TEXT SUMMARIZER - COMPLETE SYSTEM DEBUG AUDIT")
    print("=" * 70)

    # 1. Imports
    print("\n[1/6] Checking Python & Core Library Imports...")
    try:
        import fastapi, uvicorn, pydantic, google.genai, sqlalchemy, psycopg, dotenv, pytest, httpx
        print(f"  ✓ Python:     {sys.version.split()[0]}")
        print(f"  ✓ FastAPI:    {fastapi.__version__}")
        print(f"  ✓ Pydantic:   {pydantic.__version__}")
        print(f"  ✓ SQLAlchemy: {sqlalchemy.__version__}")
        print(f"  ✓ Psycopg:    {psycopg.__version__}")
        print(f"  ✓ Pytest:     {pytest.__version__}")
        print(f"  ✓ HTTPX:      {httpx.__version__}")
    except Exception as exc:
        print(f"  ✗ Import Error: {exc}")
        return False

    # 2. Environment Variables
    print("\n[2/6] Checking Environment Variables (.env)...")
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    db_url = os.getenv("DATABASE_URL")

    if api_key and len(api_key.strip()) > 10:
        print(f"  ✓ GEMINI_API_KEY: Configured (starts with {api_key[:6]}..., length {len(api_key)})")
    else:
        print("  ✗ GEMINI_API_KEY: Missing or unconfigured in .env!")
        return False

    if db_url:
        masked = db_url.split("@")[-1] if "@" in db_url else db_url
        print(f"  ✓ DATABASE_URL:   Configured (Target: {masked})")
    else:
        print("  ✗ DATABASE_URL: Missing in .env!")
        return False

    # 3. PostgreSQL Database
    print("\n[3/6] Checking PostgreSQL Database Connection & Tables...")
    try:
        from app.database import engine, SessionLocal
        from app.models import Summary
        from sqlalchemy import inspect, select

        with engine.connect() as conn:
            print("  ✓ PostgreSQL socket connection: ACTIVE")

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "summaries" in tables:
            cols = [c["name"] for c in inspector.get_columns("summaries")]
            print(f"  ✓ Table 'summaries': EXISTS (columns: {cols})")
            db = SessionLocal()
            count = len(db.scalars(select(Summary)).all())
            print(f"  ✓ Total stored records in database: {count}")
            db.close()
        else:
            print("  ✗ Table 'summaries' NOT found in database!")
            return False
    except Exception as exc:
        print(f"  ✗ Database Connection Error: {exc}")
        return False

    # 4. Google Gemini AI Cloud
    print("\n[4/6] Checking Google Gemini Live Cloud API...")
    try:
        from app.services import summarize_text
        t0 = time.time()
        test_summary = summarize_text("FastAPI and Gemini integration is operational.")
        elapsed = round(time.time() - t0, 2)
        print(f"  ✓ Gemini API live inference succeeded in {elapsed}s")
        print(f"  ✓ Sample response: \"{test_summary}\"")
    except Exception as exc:
        print(f"  ✗ Gemini AI Error: {exc}")
        return False

    # 5. FastAPI Endpoints
    print("\n[5/6] Checking FastAPI Application Endpoints...")
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app, follow_redirects=False)

        # Health
        r_health = client.get("/health")
        assert r_health.status_code == 200
        print(f"  ✓ GET /health:    200 OK -> {r_health.json()}")

        # Root redirect
        r_root = client.get("/")
        assert r_root.status_code == 307
        print(f"  ✓ GET / (Root):   307 Redirect -> {r_root.headers.get('location')}")

        # Summarize valid
        r_sum = client.post("/summarize", json={"text": "Artificial intelligence accelerates diagnostic healthcare."})
        assert r_sum.status_code == 200
        print(f"  ✓ POST /summarize (Valid input): 200 OK")

        # Summarize validation rejection
        r_empty = client.post("/summarize", json={"text": "   "})
        assert r_empty.status_code == 422
        print(f"  ✓ POST /summarize (Empty input): 422 Unprocessable Entity correctly rejected")

        # Summaries query
        r_list = client.get("/summaries?limit=3")
        assert r_list.status_code == 200
        print(f"  ✓ GET /summaries: 200 OK -> retrieved {len(r_list.json())} records")
    except Exception as exc:
        print(f"  ✗ Endpoint Error: {exc}")
        return False

    # 6. Pytest Suite
    print("\n[6/6] Checking Pytest Automated Suite (12 Tests)...")
    try:
        import pytest
        code = pytest.main(["-q", str(PROJECT_ROOT / "tests" / "test_api.py")])
        if code == 0:
            print("  ✓ All 12 automated unit & integration tests PASSED!")
        else:
            print(f"  ✗ Pytest failed with exit code: {code}")
            return False
    except Exception as exc:
        print(f"  ✗ Pytest Error: {exc}")
        return False

    print("\n" + "=" * 70)
    print("      AUDIT RESULT: 100% HEALTHY - ALL SYSTEMS WORKING PERFECTLY")
    print("=" * 70 + "\n")
    return True


if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
