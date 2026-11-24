# AI Text Summarizer REST API

A high-performance, production-ready AI Text Summarization REST API built with **FastAPI**, **Google Gemini API** (via the official `google-genai` SDK), and **PostgreSQL** with **SQLAlchemy ORM**.

---

## 1. Project Overview

The **AI Text Summarizer API** is an enterprise-grade backend service designed to accept long-form text, validate its structure, generate a concise, objective summary using Google's hosted Gemini generative foundation models, and persist both the original text and generated summary with timestamps in a PostgreSQL relational database.

### Core Architectural Principles
- **Separation of Concerns**: Schema validation, database models, AI external services, and routing are strictly decoupled into independent modules.
- **Zero Local AI Footprint**: Consumes Google's hosted cloud AI infrastructure; no local LLMs are downloaded or run locally.
- **Defensive Error Handling**: Exhaustive exception mapping for timeouts, quota limits, missing credentials, and database failures.
- **100% Hermetic Automated Testing**: Comprehensive Pytest suite guaranteeing deterministic verification without incurring cloud costs.

---

## 2. Key Features

- **Pydantic v2 Data Validation**: Enforces string boundaries, non-empty content, and custom whitespace validators, rejecting malformed requests with standard `422 Unprocessable Entity` responses.
- **Google Gemini Hosted AI Integration**: Leverages Google's official `google-genai` Python SDK with executive system instructions, deterministic temperature (`0.2`), and dynamic model fallback (`gemini-3.1-flash-lite`).
- **Robust Timeout & Error Handling**: Transparently maps third-party failures to standard HTTP codes (`504 Gateway Timeout`, `429 Too Many Requests`, `502 Bad Gateway`).
- **PostgreSQL Persistence with SQLAlchemy 2.0**: Records every summarization with automatic primary keys and UTC timestamps.
- **Automatic Connection Recovery**: Utilizes SQLAlchemy's `pool_pre_ping=True` to detect and recover from stale database connections.
- **Dual Client Interfaces**: Interactive Swagger UI (`/docs`) and a standalone interactive terminal client (`client.py`).
- **CLI Database Verification**: `verify_db.py` script allows rapid database inspection directly from the terminal.

---

## 3. Technology Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Language** | Python | 3.10+ / 3.14 | Modern backend language with native type hinting |
| **Framework** | FastAPI | 0.115+ | High-throughput, async web framework |
| **ASGI Server** | Uvicorn | 0.30+ | Lightning-fast ASGI HTTP server |
| **Validation** | Pydantic v2 | 2.8+ | Runtime schema validation and serialization |
| **Cloud AI** | Google GenAI SDK | 0.1.1+ | Official SDK for Google Gemini hosted models |
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
    FastAPI->>Pydantic: Parse & Validate JSON (SummarizeRequest)
    alt Input Invalid (Empty / Whitespace / Malformed)
        Pydantic-->>Client: 422 Unprocessable Entity
    else Input Valid
        FastAPI->>Gemini: summarize_text(text)
        Gemini->>GoogleCloud: HTTPS POST (gemini-3.1-flash-lite, temp=0.2)
        alt Cloud Timeout / Rate Limit
            GoogleCloud-->>FastAPI: Error (Timeout / 429)
            FastAPI-->>Client: 504 Gateway Timeout or 429 Rate Limit
        else Cloud Success
            GoogleCloud-->>Gemini: Summary Response
            Gemini-->>FastAPI: "Summary string..."
            FastAPI->>ORM: Session.add(Summary(...))
            FastAPI->>ORM: Session.commit()
            ORM->>Postgres: INSERT INTO summaries (...)
            Postgres-->>ORM: Commit OK
            FastAPI-->>Client: 200 OK { "summary": "..." }
        end
    end
```

---

## 5. Detailed Code Walkthrough by Assignment Topic

### Topic 1: FastAPI Service & the `POST /summarize` Endpoint (`app/main.py`)

The main entry point exposes the REST endpoints and coordinates validation, AI summarization, and database persistence:

```python
@app.post(
    "/summarize",
    response_model=SummarizeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Summarization"],
    summary="Generate and save text summary",
)
def summarize(
    request: SummarizeRequest,
    db: Session = Depends(get_db),
) -> SummarizeResponse:
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
        db.rollback()  # Rollback on database failure
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred while persisting summary: {str(exc)}",
        ) from exc

    return SummarizeResponse(summary=summary)
```

#### Code Explanation:
1. **`request: SummarizeRequest`**: FastAPI inspects the parameter type annotation. Because `SummarizeRequest` inherits from `pydantic.BaseModel`, FastAPI automatically extracts and validates the JSON body from the HTTP request.
2. **`db: Session = Depends(get_db)`**: Uses FastAPI's **Dependency Injection** system. It requests a thread-safe database session from `get_db()`, ensuring the session is opened before the handler runs and closed when the response completes.
3. **`response_model=SummarizeResponse`**: Sanitizes the outgoing data, guaranteeing the client receives strictly `{"summary": "..."}` and stripping any accidental internal data leaks.
4. **`db.rollback()`**: If an error occurs during `db.commit()` (e.g. disk failure or lost connection), `db.rollback()` cancels the pending transaction so the database socket remains healthy.

---

### Topic 2: Hosted AI API Integration with Google Gemini (`app/services.py`)

Interacts with Google's hosted foundation models over HTTPS. **No model is run or downloaded locally**:

```python
def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() in ("", "your_gemini_api_key_here"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not configured. Please set a valid Gemini API key in your .env file.",
        )

    # Use standard httpx.Client to guarantee fast, reliable TLS/SSL connections on Windows
    std_httpx_client = httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)

    return genai.Client(
        api_key=api_key.strip(),
        http_options=types.HttpOptions(httpx_client=std_httpx_client),
    )
```

```python
def summarize_text(text: str, client: Optional[genai.Client] = None) -> str:
    if client is None:
        client = get_gemini_client()

    config = types.GenerateContentConfig(
        system_instruction=(
            "You are an expert executive summarizer. Analyze the input text carefully and produce a concise, "
            "accurate, and coherent summary capturing the core ideas, primary insights, and essential takeaways. "
            "Return strictly the summary text."
        ),
        temperature=0.2,       # Low temperature for factual, deterministic summaries
        max_output_tokens=1024,# Prevent runaway generation costs
    )

    # Dynamic fallback across production Gemini models
    for target_model in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=f"Please summarize the following text concisely:\n\n{text}",
                config=config,
            )
            if response and response.text:
                return response.text.strip()
        except ClientError as exc:
            if getattr(exc, "code", 400) == 429:
                raise HTTPException(status_code=429, detail="Gemini API quota exceeded.") from exc
            continue
```

#### Code Explanation:
1. **`from google import genai`**: Uses the official, unified Google GenAI SDK.
2. **`system_instruction`**: Sets the persona of the AI, eliminating conversational filler (such as *"Sure! Here is your summary:"*).
3. **`temperature=0.2`**: Low temperature restricts creativity and hallucination, enforcing high factual accuracy.
4. **Defensive Error Mapping**: Maps Google Cloud errors to REST status codes:
   - Timeout (>30s) ➔ `504 Gateway Timeout`
   - Quota limit ➔ `429 Too Many Requests`
   - Invalid Key ➔ `502 Bad Gateway`
   - Google Outage ➔ `502 Bad Gateway`

---

### Topic 3: Pydantic Request & Response Validation (`app/schemas.py`)

Enforces strict contracts on all incoming and outgoing data:

```python
class SummarizeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="The source text to be summarized. Cannot be empty or whitespace.",
        examples=["Type your text here..."],
    )

    @field_validator("text")
    @classmethod
    def validate_text_not_blank(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("The 'text' field cannot be empty or contain only whitespace.")
        return stripped_value


class SummarizeResponse(BaseModel):
    summary: str = Field(
        ...,
        description="The AI-generated concise summary of the input text.",
    )
```

#### Code Explanation:
1. **`Field(..., min_length=1, max_length=50000)`**: The `...` (Ellipsis) specifies that `text` is strictly required. String length boundaries prevent zero-length or excessively huge payloads.
2. **`@field_validator("text")`**: Intercepts the raw string before model instantiation. If a client sends `"   "` (spaces or tabs), the validator raises a `ValueError`, which FastAPI converts into an **RFC-compliant HTTP `422 Unprocessable Entity`** error response.

---

### Topic 4: PostgreSQL Persistence with SQLAlchemy ORM (`app/database.py` & `app/models.py`)

Handles relational database connections, pooling, and table mapping:

```python
# app/database.py
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Proactively pings connection to detect dropped sockets
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Guarantees connection is returned to pool after request
```

```python
# app/models.py
class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

#### Code Explanation:
1. **`pool_pre_ping=True`**: Issues a lightweight `SELECT 1` ping before handing a pooled connection to a route. If PostgreSQL or a proxy closed the socket due to idle timeout, SQLAlchemy seamlessly reconnects.
2. **`yield db` / `finally: db.close()`**: The generator ensures the session is closed and returned to the pool even if an unhandled exception occurs inside the route.
3. **`server_default=func.now()`**: PostgreSQL itself assigns the UTC timestamp upon insertion, ensuring timestamp accuracy regardless of server clock discrepancies.

---

### Topic 5: Incremental Git Workflow

Development was performed through **incremental semantic commits** rather than a single large upload:

```text
0302517 feat: add interactive terminal client and clean placeholder examples
0054c5b fix: redirect root to docs and handle favicon
f4ee949 refactor: remove custom UI and unused code
66eabe4 feat: add interactive web UI and optimize Gemini client
5fe2073 fix: enhance env path resolution and add run.py launcher
c39cfcf docs: add project README
ab8202b test: add API tests and error handling
460069d feat: add PostgreSQL persistence
8033847 feat: integrate Gemini summarization API
d4e23eb feat: add Pydantic request and response schemas
ed96979 feat: add FastAPI application
55b3b27 chore: initialize project structure
```

---

## 6. How to Run the Project (Windows 11 PowerShell)

### Step 1: Open Terminal in Project Directory
```powershell
cd "C:\Users\prajw\.gemini\antigravity\scratch\ai-text-summarizer"
```

### Step 2: Configure Environment Variables
Copy the template and edit your `.env`:
```powershell
Copy-Item .env.example .env
notepad .env
```
Fill in your credentials:
```ini
GEMINI_API_KEY=AIzaSy...your_gemini_key...
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/summarizer_db
```

### Step 3: Start the Server
```powershell
python run.py
```
- Server URL: **http://127.0.0.1:8000**
- Swagger UI Documentation: **http://127.0.0.1:8000/docs**

### Step 4: Use the Interactive Terminal Client (Easiest Way to Test)
Open PowerShell and run:
```powershell
python client.py
```
Type any custom text at the prompt and press Enter to see your AI summary immediately!

### Step 5: Verify Stored Database Records
```powershell
python verify_db.py
```

---

## 7. Automated Testing with Pytest

Run the comprehensive test suite:
```powershell
python -m pytest -v tests/test_api.py
```

### Test Scenarios Covered (All 12 Passed in ~2s)
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

## 8. What Was Learned

1. **Decoupled 3-Tier Architecture**: Keeping Pydantic validation, Gemini cloud logic, and SQLAlchemy persistence in separate modules allows individual components to be modified or tested without affecting the rest of the application.
2. **Modern Google GenAI SDK (`google-genai`)**: Using the unified official SDK, handling model lifecycle, dynamic fallback across available models, and configuring `httpx.Client` for fast TLS connections on Windows.
3. **Defensive Error Translation**: External APIs fail unpredictably. Transparently translating external timeouts and rate limits into RFC-compliant HTTP status codes (`504`, `429`, `502`) is critical for production reliability.
4. **Relational Persistence & Pool Management**: Using SQLAlchemy 2.0 with Psycopg 3, configuring connection pre-pinging (`pool_pre_ping=True`) to avoid stale connection errors, and using transactional rollbacks (`db.rollback()`) to protect data integrity.
5. **Zero-Cost Hermetic Testing**: Testing external cloud AI APIs without spending money by mocking SDK calls with `unittest.mock.patch` and overriding database sessions with an in-memory SQLite database (`StaticPool`).
6. **Git Hygiene**: Practicing disciplined, incremental commits matching feature development stages (`chore:`, `feat:`, `test:`, `docs:`, `fix:`, `refactor:`).

---

## 9. Future Improvements

1. **Redis Caching**: Cache summaries using a SHA-256 hash of the input text as the cache key to avoid duplicate LLM calls and reduce API costs.
2. **Asynchronous Background Processing**: For very long documents (e.g. 50+ pages), offload processing to Celery or Redis queues with a task status endpoint (`GET /tasks/{task_id}`).
3. **Streaming Responses (SSE)**: Implement a Server-Sent Events endpoint (`POST /summarize/stream`) to stream summary tokens back in real-time as Gemini generates them.
4. **User Authentication & Quotas**: Add JWT authentication (OAuth2) and per-user daily rate limits using Redis token buckets.
