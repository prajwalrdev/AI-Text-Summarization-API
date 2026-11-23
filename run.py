"""
Convenience launcher for the AI Text Summarizer API server.
Can be executed directly with: python run.py
"""

import sys
from pathlib import Path
import uvicorn

# Ensure the project root directory is on the Python module search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    print("\nStarting AI Text Summarizer API on http://127.0.0.1:8000 ...")
    print("Swagger UI Documentation: http://127.0.0.1:8000/docs\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
