# C Language AI Text Summarizer Backend

A low-level, high-performance C language implementation of the AI Text Summarization REST API.

---

## 1. Architecture Overview (C vs Python)

| Feature | Python Implementation (`app/`) | C Language Implementation (`c-backend/`) |
| :--- | :--- | :--- |
| **Web Server** | Uvicorn (ASGI Event Loop) | Native Windows TCP Sockets (`Winsock2` / `ws2_32.lib`) |
| **Routing & Framework** | FastAPI (Decorators & Dependency Injection) | Manual HTTP/1.1 parsing (`server.c`) |
| **Validation** | Pydantic v2 Models (`SummarizeRequest`) | Manual JSON parsing & string validation (`extract_json_text`) |
| **Cloud AI HTTPS Client** | `google-genai` Python SDK | Native Windows **WinHTTP API** (`winhttp.lib`) over TLS/HTTPS |
| **PostgreSQL Driver** | SQLAlchemy ORM + Psycopg 3 | PostgreSQL Native C Client (`libpq-fe.h` / `libpq.lib`) |
| **Memory Model** | Automatic Garbage Collection (PVM) | Explicit manual allocation (`malloc` / `free`) |
| **Binary Output** | Bytecode `.pyc` interpreted by Python | Compiled native machine code (`server.exe`) |

---

## 2. File Structure

```text
c-backend/
│
├── server.c      # Main HTTP server, socket listener (port 8000), routing, validation
├── gemini.h      # Header definition for Gemini cloud AI integration
├── gemini.c      # Windows WinHTTP HTTPS client calling Google Generative Language API
├── db.h          # Header definition for PostgreSQL persistence
├── db.c          # PostgreSQL client integration using libpq
├── build.bat     # Windows batch compilation script (GCC / MSVC)
└── README.md     # Documentation and compilation guide
```

---

## 3. Endpoints Implemented in C

### `GET /health`
Returns HTTP 200 OK:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "language": "C"
}
```

### `POST /summarize`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "text": "Your long text here..."
  }
  ```
- **Validation**: Rejects empty strings or whitespace with HTTP `422 Unprocessable Entity`:
  ```json
  {
    "detail": "The 'text' field cannot be empty or contain only whitespace."
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "summary": "AI generated concise summary."
  }
  ```

---

## 4. How to Compile and Run on Windows 11

### Step 1: Install a C Compiler (If Not Already Installed)
You can use either:
- **MinGW-w64 (GCC)**: Download from [winlibs.com](https://winlibs.com/) or install via [MSYS2](https://www.msys2.org/).
- **Visual Studio C++ Build Tools**: Install from Microsoft Visual Studio Installer.

### Step 2: Compile the Code
Run the included build script:
```cmd
build.bat
```
*(Or compile directly with GCC)*:
```cmd
gcc -O2 -Wall server.c gemini.c db.c -o server.exe -lws2_32 -lwinhttp
```

### Step 3: Run the Server
```cmd
server.exe
```

The server will listen on **`http://127.0.0.1:8000`** and process `POST /summarize` requests using your `.env` configuration.
