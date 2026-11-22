# AI Text Summarizer REST API

A high-performance, production-ready AI Text Summarization REST API built with **FastAPI**, **Google Gemini API** (via the official `google-genai` SDK), and **PostgreSQL** with **SQLAlchemy ORM**.

---

## 1. Project Overview

The **AI Text Summarizer API** is an enterprise-grade backend service designed to accept long-form text, validate its structure, generate a concise, objective summary using Google's hosted Gemini generative foundation models, and persist both the original text and generated summary with timestamps in a PostgreSQL relational database.

This project strictly adheres to clean architecture principles:
- **Separation of Concerns**: Schema validation, database models, AI external services, and routing are strictly decoupled into independent modules.
- **Zero Local AI Footprint**: Consumes Google's hosted cloud AI infrastructure; no local LLMs are downloaded or run locally.
- **Defensive Error Handling**: Exhaustive exception mapping for timeouts, quota limits, missing credentials, and database failures.
- **100% Mocked Automated Testing**: Comprehensive Pytest suite guaranteeing deterministic verification without incurring cloud costs.

---

## 2. Key Features

- **Pydantic Data Validation**: Enforces string boundaries, non-empty content, and custom whitespace validators, rejecting malformed requests with standard `422 Unprocessable Entity` responses.
- **Google Gemini 2.5 Flash Integration**: Leverages Google's official `google-genai` Python SDK with executive system instructions, deterministic temperature (`0.2`), and token caps.
- **Robust Timeout & Error Handling**: Transparently maps third-party failures to standard HTTP codes (`504 Gateway Timeout`, `429 Too Many Requests`, `502 Bad Gateway`).
- **PostgreSQL Persistence with SQLAlchemy 2.0**: Records every summarization with automatic primary keys and UTC timestamps.
- **Automatic Connection Recovery**: Utilizes SQLAlchemy's `pool_pre_ping=True` to detect and recover from stale database connections.
- **Interactive Documentation**: Auto-generated Swagger UI (`/docs`) and ReDoc (`/redoc`) with schema definitions and request examples.
- **Standalone CLI Verification**: `verify_db.py` script allows rapid database inspection directly from the terminal.

---

## 3. Technology Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Language** | Python | 3.10+ / 3.14 | Modern backend language with native typing |
| **Framework** | FastAPI | 0.115+ | High-throughput, async web framework |
| **ASGI Server** | Uvicorn | 0.30+ | Lightning-fast ASGI HTTP server |
| **Validation** | Pydantic v2 | 2.8+ | Runtime schema validation and serialization |
| **Cloud AI** | Google GenAI SDK | 0.1.1+ | Official SDK for Google Gemini models |
| **Database** | PostgreSQL | 14+ | Relational persistence store |
| **ORM** | SQLAlchemy | 2.0+ | Modern mapped-column Object-Relational Mapper |
| **DB Driver** | Psycopg 3 | 3.2+ | Modern PostgreSQL adapter for Python |
| **Configuration**| python-dotenv | 1.0+ | Secure `.env` environment variable management |
| **Testing** | Pytest & HTTPX | 8.0+ / 0.27+ | Test runner, fixtures, and FastAPI TestClient |

---

## 4. Architecture & Request Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant ASGI as Uvicorn (ASGI)
    participant FastAPI as FastAPI Router
    participant Pydantic as Pydantic Validation
    participant Gemini as Google GenAI SDK
    participant GoogleCloud as Google Gemini Cloud
    participant ORM as SQLAlchemy ORM
    participant Postgres as PostgreSQL DB

    Client->>ASGI: POST /summarize { "text": "..." }
    ASGI->>FastAPI: Forward Request
    FastAPI->>Pydantic: Parse & Validate JSON
    alt Input Invalid (Empty / Whitespace / Malformed)
        Pydantic-->>Client: 422 Unprocessable Entity
    else Input Valid
        FastAPI->>Gemini: summarize_text(text)
        Gemini->>GoogleCloud: HTTPS POST (gemini-2.5-flash, temp=0.2)
        alt Cloud Timeout / Rate Limit
            GoogleCloud-->>FastAPI: Error (Timeout / 429)
            FastAPI-->>Client: 504 Gateway Timeout or 429 Rate Limit
        else Cloud Success
            GoogleCloud-->>Gemini: Summary Response
            Gemini-->>FastAPI: "Summary string..."
            FastAPI->>ORM: Session.add(Summary(...))
            ORM->>Postgres: INSERT INTO summaries (...)
            Postgres-->>ORM: Commit OK
            FastAPI-->>Client: 200 OK { "summary": "..." }
        end
    end
```

---

## 5. Project Structure

```
ai-text-summarizer/
│
├── app/
│   ├── __init__.py           # Application package identifier
│   ├── main.py               # FastAPI app, routing, and lifespan
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── database.py           # SQLAlchemy engine, sessionmaker, get_db
│   ├── models.py             # SQLAlchemy ORM database models
│   └── services.py           # Gemini API integration and error handling
│
├── tests/
│   ├── __init__.py           # Tests package identifier
│   └── test_api.py           # Pytest suite with complete mock coverage
│
├── .env                      # Local secrets (git ignored)
├── .env.example              # Environment variables template
├── .gitignore                # Protects secrets, cache, and virtualenvs
├── requirements.txt          # Production and testing dependencies
├── verify_db.py              # Standalone CLI tool to verify database records
└── README.md                 # Complete project documentation
```

---

## 6. Installation & Setup (Windows 11 PowerShell)

### Step 1: Clone or Navigate to Project
```powershell
cd "C:\Users\prajw\.gemini\antigravity\scratch\ai-text-summarizer"
```

### Step 2: (Optional) Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 7. Environment Configuration

### Step 1: Create `.env` from Template
```powershell
Copy-Item .env.example .env
```

### Step 2: Configure Keys
Open `.env` in a text editor and fill in your values:

```ini
# Google Gemini API Key (Obtain from https://aistudio.google.com/)
GEMINI_API_KEY=AIzaSy...your_actual_key_here...

# PostgreSQL Database Connection URL
# Format: postgresql+psycopg://<username>:<password>@<host>:<port>/<database_name>
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/summarizer_db
```

> [!TIP]
> **Instant Offline / Local Testing**: If you don't have a local PostgreSQL server running yet, you can set `DATABASE_URL=sqlite:///./local_dev.db` in `.env` to test end-to-end immediately without installing PostgreSQL.

---

## 8. How to Run and Compile the Project

### Compilation / Bytecode Verification
Python bytecode can be pre-compiled to check for syntax and import errors:
```powershell
python -m compileall app tests
```

### Start the Development Server
```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Server URL: **http://127.0.0.1:8000**
- Interactive Swagger UI: **http://127.0.0.1:8000/docs**
- ReDoc Documentation: **http://127.0.0.1:8000/redoc**

---

## 9. API Reference & Sample Requests

### Endpoint: Health Check
- **Method**: `GET /health`
- **Response** (`200 OK`):
  ```json
  {
    "status": "healthy",
    "version": "1.0.0"
  }
  ```

### Endpoint: Main Summarization
- **Method**: `POST /summarize`
- **Headers**: `Content-Type: application/json`
- **Sample Request**:
  ```json
  {
    "text": "Artificial intelligence is transforming industries worldwide by automating repetitive tasks, uncovering deep data insights, and enabling new creative workflows. Modern large language models can understand context and generate human-like summaries."
  }
  ```
- **Sample Response** (`200 OK`):
  ```json
  {
    "summary": "Artificial intelligence transforms global industries through automation, data insights, and advanced language models."
  }
  ```

### Endpoint: List Stored Summaries
- **Method**: `GET /summaries?limit=10`
- **Response** (`200 OK`):
  ```json
  [
    {
      "id": 1,
      "original_text": "Artificial intelligence is transforming industries...",
      "generated_summary": "Artificial intelligence transforms global industries...",
      "created_at": "2026-11-22T01:09:45"
    }
  ]
  ```

---

## 10. Database Record Verification

Verify records written to the database using the included CLI tool:
```powershell
python verify_db.py
```

---

## 11. Automated Testing

Execute the test suite using `pytest`:

```powershell
python -m pytest -v tests/test_api.py
```

### Test Scenarios Covered
| Test | Condition Tested | Expected Status |
| :--- | :--- | :--- |
| `test_health_check` | Service liveness probe | `200 OK` |
| `test_summarize_valid_input_success` | Valid text payload | `200 OK` + DB Insert |
| `test_get_summaries_endpoint` | Query database records | `200 OK` |
| `test_summarize_empty_input` | Empty string (`""`) | `422 Unprocessable Entity` |
| `test_summarize_whitespace_only_input`| Whitespace only (`"   "`) | `422 Unprocessable Entity` |
| `test_summarize_missing_text_field` | Missing `"text"` field | `422 Unprocessable Entity` |
| `test_summarize_invalid_json_payload` | Malformed JSON syntax | `422 Unprocessable Entity` |
| `test_summarize_gemini_missing_api_key`| Missing `.env` API key | `500 Internal Server Error` |
| `test_summarize_gemini_timeout` | Google API timeout (>30s)| `504 Gateway Timeout` |
| `test_summarize_gemini_rate_limit` | Quota exhausted (429) | `429 Too Many Requests` |
| `test_summarize_gemini_upstream_server_error` | Google 5xx server error | `502 Bad Gateway` |
| `test_summarize_database_failure_rollback`| DB write failure | `500` + Clean Rollback |

---

## 12. What Was Learned

- **Decoupled Architecture**: Separating Pydantic validation, SQLAlchemy persistence, and Gemini business logic makes testing effortless.
- **Modern Google GenAI SDK**: Utilizing the unified `google-genai` library with `types.GenerateContentConfig` and `types.HttpOptions`.
- **Defensive Error Mapping**: Translating external cloud provider exceptions into standardized REST HTTP status codes (`504`, `429`, `502`).
- **Transactional Integrity**: Managing database sessions with FastAPI's `Depends(get_db)` and executing explicit rollbacks on failures to prevent connection leaks.
- **Mocking Without Paid Cloud Costs**: Testing all edge cases deterministically using `unittest.mock` and in-memory SQLite fixtures.

---

## 13. Future Improvements

1. **Redis Caching**: Cache summaries of identical text hashes to avoid redundant LLM calls.
2. **Asynchronous Background Processing**: Offload very large document summarization to Celery / Redis background worker queues.
3. **Streaming Responses**: Enable Server-Sent Events (SSE) / streaming endpoint `POST /summarize/stream` to render summaries token-by-token.
4. **User Authentication**: Implement JWT bearer token authorization to associate summaries with specific authenticated users.
