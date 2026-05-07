"""
Data models, constants, and exceptions for the QR Code service.
"""

import string
from dataclasses import dataclass, field
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE62_ALPHABET: str = string.ascii_uppercase + string.ascii_lowercase + string.digits

SHORT_ID_LENGTH: int = 6
# 62^6 = 56,800,235,584 unique IDs — well above the 1 billion target.
# In production: use Redis INCR → Base62 to eliminate collisions entirely
# at the cost of sequential (predictable) IDs.

MAX_URL_LENGTH: int = 20
# Requirement: ASCII only, max 20 characters.

BASE_REDIRECT_URL: str = "http://localhost:8000"
# In production: "https://qr.yourdomain.com"
# Kept as short as possible — every character in the QR payload adds
# modules to the QR matrix, reducing scanability.

QR_BOX_SIZE: int = 10   # pixels per QR module
QR_BORDER: int = 4      # quiet zone width in modules (spec minimum is 4)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class User:
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    # Production: PostgreSQL `users` table
    #   user_id    VARCHAR PRIMARY KEY  (or UUID)
    #   created_at TIMESTAMPTZ NOT NULL DEFAULT now()


@dataclass
class QRCodeRecord:
    qr_id: str           # 6-char Base62 short ID — PRIMARY KEY in PostgreSQL
    user_id: str         # owner — FOREIGN KEY → users.user_id
    original_url: str    # the URL the user submitted
    redirect_url: str    # full URL embedded in QR image (e.g. http://localhost:8000/aB3x9Z)
    created_at: datetime = field(default_factory=datetime.utcnow)
    scan_count: int = 0  # incremented on each redirect hit
    # Production note on scan_count:
    # Do NOT increment synchronously on the redirect path — that adds a DB write
    # to the hot path and would violate the < 100 ms SLA under high scan load.
    # Instead: emit a Kafka event on each scan, consume it in a background
    # counter service that batches increments to PostgreSQL.


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class QRCodeError(Exception):
    """Base exception for all QR code service errors."""

class URLValidationError(QRCodeError):
    """Raised when the submitted URL fails validation. → HTTP 422"""

class QRCodeNotFoundError(QRCodeError):
    """Raised when a qr_id does not exist in storage. → HTTP 404"""

class UserNotFoundError(QRCodeError):
    """Raised when a user_id does not exist in storage. → HTTP 404"""

class DuplicateURLError(QRCodeError):
    """Raised when a user already has a QR code for this exact URL. → HTTP 409"""
