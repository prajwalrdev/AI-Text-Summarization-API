"""
Automated Pytest Suite for AI Text Summarization API.
Tests request validation, Gemini integration error handling, database persistence, and rollback.
All external API calls are mocked to ensure deterministic, fast, zero-cost execution.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from google.genai.errors import ClientError, ServerError
import httpx
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Summary


# ==============================================================================
# PYTEST FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def in_memory_engine():
    """
    Creates an isolated in-memory SQLite database engine for testing.
    StaticPool ensures all sessions connect to the same in-memory SQLite instance.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(in_memory_engine) -> Session:
    """
    Provides a clean, transaction-managed database session for each test.
    Cleans up any rows inserted after each test runs.
    """
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=in_memory_engine,
    )
    session = TestingSessionLocal()
    yield session
    # Clean up records after each test to keep tests isolated
    session.query(Summary).delete()
    session.commit()
    session.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """
    TestClient fixture with FastAPI dependency override injecting the test database session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_gemini():
    """
    Mocks the get_gemini_client function in app.services.
    Returns a configured mock response without hitting Google servers.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a concise, AI-generated summary of the input text."
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.get_gemini_client", return_value=mock_client) as patcher:
        yield patcher, mock_client


# ==============================================================================
# 1. GENERAL & HEALTH CHECK TESTS
# ==============================================================================

def test_health_check(client: TestClient):
    """
    Verify GET /health returns 200 OK with correct status payload.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


# ==============================================================================
# 2. SUCCESSFUL SUMMARIZATION & DATABASE PERSISTENCE TESTS
# ==============================================================================

def test_summarize_valid_input_success(client: TestClient, db_session: Session, mock_gemini):
    """
    Verify that a valid POST /summarize request:
    1. Returns HTTP 200 OK with the generated summary.
    2. Persists the original text, summary, and timestamp to the summaries table.
    """
    patcher, mock_client = mock_gemini
    sample_text = (
        "Artificial intelligence is rapidly modernizing backend development. "
        "By automating code analysis, generating real-time insights, and enhancing APIs, "
        "AI enables developers to build scalable and robust applications faster than ever."
    )

    response = client.post("/summarize", json={"text": sample_text})

    # 1. Verify HTTP Response
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert body["summary"] == "This is a concise, AI-generated summary of the input text."

    # 2. Verify Database Persistence
    saved_record = db_session.query(Summary).first()
    assert saved_record is not None
    assert saved_record.original_text == sample_text
    assert saved_record.generated_summary == "This is a concise, AI-generated summary of the input text."
    assert isinstance(saved_record.created_at, datetime)


def test_get_summaries_endpoint(client: TestClient, db_session: Session, mock_gemini):
    """
    Verify that GET /summaries returns stored records accurately.
    """
    # Create two records via POST /summarize
    client.post("/summarize", json={"text": "First article to summarize."})
    client.post("/summarize", json={"text": "Second article to summarize."})

    response = client.get("/summaries")
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 2
    assert records[0]["original_text"] == "Second article to summarize."  # Ordered desc
    assert records[1]["original_text"] == "First article to summarize."


# ==============================================================================
# 3. INPUT VALIDATION & INVALID DATA TESTS (PYDANTIC)
# ==============================================================================

def test_summarize_empty_input(client: TestClient):
    """
    Verify that empty text ('') triggers HTTP 422 Unprocessable Entity.
    """
    response = client.post("/summarize", json={"text": ""})
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("at least 1 character" in err["msg"] or "cannot be empty" in err["msg"] for err in errors)


def test_summarize_whitespace_only_input(client: TestClient):
    """
    Verify that whitespace-only input ('   ') triggers our custom field validator and returns 422.
    """
    response = client.post("/summarize", json={"text": "   \n\t   "})
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("The 'text' field cannot be empty or contain only whitespace." in err["msg"] for err in errors)


def test_summarize_missing_text_field(client: TestClient):
    """
    Verify that missing 'text' key in JSON triggers HTTP 422.
    """
    response = client.post("/summarize", json={})
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"] == ["body", "text"] for err in errors)


def test_summarize_invalid_json_payload(client: TestClient):
    """
    Verify that malformed / non-parseable JSON triggers HTTP 422.
    """
    response = client.post(
        "/summarize",
        content="This is not valid JSON {",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


# ==============================================================================
# 4. GEMINI API FAILURE & TIMEOUT TESTS
# ==============================================================================

def test_summarize_gemini_missing_api_key(client: TestClient):
    """
    Verify that an unconfigured GEMINI_API_KEY returns HTTP 500 with a clear message.
    """
    with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
        response = client.post("/summarize", json={"text": "Valid text input."})
        assert response.status_code == 500
        assert "GEMINI_API_KEY is not configured" in response.json()["detail"]


def test_summarize_gemini_timeout(client: TestClient, mock_gemini):
    """
    Verify that upstream Gemini API timeouts trigger HTTP 504 Gateway Timeout.
    """
    patcher, mock_client = mock_gemini
    mock_client.models.generate_content.side_effect = httpx.TimeoutException("Connection timed out")

    response = client.post("/summarize", json={"text": "Valid text input."})
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]


def test_summarize_gemini_rate_limit(client: TestClient, mock_gemini):
    """
    Verify that Gemini API quota exhaustion (429) triggers HTTP 429 Too Many Requests.
    """
    patcher, mock_client = mock_gemini
    client_error = ClientError(429, {"error": {"message": "Resource exhausted", "code": 429}})
    mock_client.models.generate_content.side_effect = client_error

    response = client.post("/summarize", json={"text": "Valid text input."})
    assert response.status_code == 429
    assert "quota or rate limit exceeded" in response.json()["detail"]


def test_summarize_gemini_upstream_server_error(client: TestClient, mock_gemini):
    """
    Verify that Google upstream 5xx errors trigger HTTP 502 Bad Gateway.
    """
    patcher, mock_client = mock_gemini
    server_error = ServerError(500, {"error": {"message": "Internal Google error", "code": 500}})
    mock_client.models.generate_content.side_effect = server_error

    response = client.post("/summarize", json={"text": "Valid text input."})
    assert response.status_code == 502
    assert "Google Gemini upstream service error" in response.json()["detail"]


# ==============================================================================
# 5. DATABASE FAILURE & ROLLBACK TESTS
# ==============================================================================

def test_summarize_database_failure_rollback(client: TestClient, db_session: Session, mock_gemini):
    """
    Verify that a database commit failure triggers a rollback and returns HTTP 500.
    Ensures that no orphaned or partial data is left behind.
    """
    with patch.object(Session, "commit", side_effect=SQLAlchemyError("Simulated database disk failure")):
        response = client.post("/summarize", json={"text": "Valid text to test DB rollback."})
        assert response.status_code == 500
        assert "Database error occurred while persisting summary" in response.json()["detail"]

    # Verify that database has no recorded rows due to clean rollback
    record_count = db_session.query(Summary).count()
    assert record_count == 0
