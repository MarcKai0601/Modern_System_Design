"""
Data models, constants, and exceptions for the QR Code service.
"""

import string
from dataclasses import dataclass, field
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Python 沒有 Java 的 `public static final`，習慣上用「全大寫名稱」表示常數。
# 這些是模組層級（module-level）的變數，相當於 Java 的 static field。

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
# @dataclass 是 Python 的自動生成器（類似 Java 的 Lombok @Data 或 Java 16+ record）。
# 它會自動產生 __init__（建構子）、__repr__（toString）、__eq__（equals）。
# 你只需要宣告欄位名稱和型別，不用手寫 getter/setter（Python 預設欄位可直接存取）。

@dataclass
class User:
    # 型別標注（Type Hint）：str、datetime 等。
    # 這在 Python 是選擇性的，執行時不會強制檢查（不像 Java 的編譯時型別）。
    # 但有了標注，IDE 和 mypy 等工具可以做靜態分析。
    user_id: str

    # field(default_factory=...) 的作用：
    # 如果寫成 created_at: datetime = datetime.utcnow()，Python 只會在
    # 「定義類別時」呼叫一次 utcnow()，所有實例共用同一個時間 — 這是個陷阱。
    # default_factory 讓每次建立新實例時才呼叫，等同於 Java 在建構子裡寫
    # this.createdAt = LocalDateTime.now();
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
# Python 的例外繼承寫法和 Java 相同：class Child(Parent)。
# 關鍵差異：Python 所有例外都是「非受檢例外」（unchecked），
# 不需要像 Java 的受檢例外（checked exception）在方法簽名加 throws。
# 建立自訂例外階層的目的是讓 API 層可以用 except SpecificError 精確捕捉。

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
