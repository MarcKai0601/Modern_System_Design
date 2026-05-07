"""
Modern System Design — Project Launcher

Usage:
  python main.py            # starts QR Code service on http://localhost:8000
  python -m qr_code.app     # alternative: run the QR Code module directly
"""

import uvicorn

from qr_code.app import app  # noqa: F401  (imported for uvicorn string reference)

if __name__ == "__main__":
    print("Modern System Design — QR Code Generator")
    print("=" * 42)
    print("Interactive API docs: http://localhost:8000/docs")
    print("=" * 42)
    uvicorn.run(
        "qr_code.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
