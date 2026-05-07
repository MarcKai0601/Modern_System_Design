"""
Service layer: QR image generation and business logic orchestration.
"""

import io
import time

import qrcode
from PIL import Image

from .models import (
    BASE_REDIRECT_URL,
    MAX_URL_LENGTH,
    QR_BOX_SIZE,
    QR_BORDER,
    DuplicateURLError,
    QRCodeNotFoundError,
    QRCodeRecord,
    URLValidationError,
    UserNotFoundError,
)
from .storage import InMemoryStorage, generate_short_id


class QRCodeGenerator:
    """
    Wraps the `qrcode` library to produce PNG images.

    Why embed the redirect URL (not the original URL)?
    The QR code encodes the SHORT redirect URL (e.g. http://localhost:8000/aB3x9Z).
    Scanning opens the redirect endpoint on our servers, which then resolves
    to the original URL. This indirection enables:
      - Analytics: we see every scan event
      - Future: change the destination URL without reissuing QR codes
      - Abuse detection: rate-limit or block the redirect endpoint
    """

    def generate(self, redirect_url: str) -> bytes:
        """Return a PNG image of the QR code as raw bytes."""
        qr = qrcode.QRCode(
            version=None,           # auto-size: picks the smallest version that fits the data
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            # ERROR_CORRECT_M = 15% data recovery capacity.
            # L (7%): smaller code, but less robust to physical damage.
            # H (30%): very robust, but produces a larger, denser matrix.
            # M is the practical default for printed / displayed QR codes.
            box_size=QR_BOX_SIZE,
            border=QR_BORDER,
        )
        qr.add_data(redirect_url)
        qr.make(fit=True)

        img: Image.Image = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.read()


class QRCodeService:
    """
    Business logic layer. All decision-making lives here.

    Routes are thin: they parse HTTP input and delegate to this class.
    This separation means each layer is independently testable:
      - Routes: validate HTTP shapes, status codes
      - Service: validate business rules, orchestrate operations
      - Storage: validate data persistence
    """

    def __init__(self, storage: InMemoryStorage, qr_generator: QRCodeGenerator) -> None:
        self.storage = storage
        self.qr_generator = qr_generator

    def _validate_url(self, url: str) -> None:
        if not url:
            raise URLValidationError("URL cannot be empty.")
        if len(url) > MAX_URL_LENGTH:
            raise URLValidationError(
                f"URL exceeds maximum length of {MAX_URL_LENGTH} characters (got {len(url)})."
            )
        if not url.isascii():
            raise URLValidationError("URL must contain only ASCII characters.")

    def create_qr_code(self, user_id: str, original_url: str) -> tuple[QRCodeRecord, bytes]:
        """
        Validate → deduplicate → generate ID → create QR image → persist.
        Returns (QRCodeRecord, png_bytes).
        """
        self._validate_url(original_url)
        self.storage.get_or_create_user(user_id)

        # Deduplication: same user, same URL → 409 Conflict.
        # Design choice: raise an error rather than silently return the existing record.
        # This forces the client to be intentional. Alternative (idempotent): return
        # the existing record with 200 OK — simpler for clients, harder to debug.
        if self.storage.user_has_url(user_id, original_url):
            raise DuplicateURLError(
                f"User '{user_id}' already has a QR code for URL '{original_url}'."
            )

        qr_id = generate_short_id(self.storage)
        redirect_url = f"{BASE_REDIRECT_URL}/{qr_id}"
        record = QRCodeRecord(
            qr_id=qr_id,
            user_id=user_id,
            original_url=original_url,
            redirect_url=redirect_url,
        )
        self.storage.save_qr_code(record)
        image_bytes = self.qr_generator.generate(redirect_url)
        return record, image_bytes

    def list_qr_codes(self, user_id: str) -> list[QRCodeRecord]:
        if user_id not in self.storage._users:
            raise UserNotFoundError(f"User '{user_id}' not found.")
        return self.storage.get_user_qr_codes(user_id)

    def delete_qr_code(self, user_id: str, qr_id: str) -> None:
        if user_id not in self.storage._users:
            raise UserNotFoundError(f"User '{user_id}' not found.")
        record = self.storage.get_qr_code(qr_id)
        if record is None:
            raise QRCodeNotFoundError(f"QR code '{qr_id}' not found.")
        if record.user_id != user_id:
            # Return 404, not 403. Returning 403 would confirm the QR code exists
            # and belongs to another user — leaking information.
            raise QRCodeNotFoundError(f"QR code '{qr_id}' not found.")
        self.storage.delete_qr_code(qr_id, user_id)

    def get_qr_record(self, user_id: str, qr_id: str) -> QRCodeRecord:
        """Fetch a single QR code record, verifying ownership."""
        record = self.storage.get_qr_code(qr_id)
        if record is None or record.user_id != user_id:
            raise QRCodeNotFoundError(f"QR code '{qr_id}' not found.")
        return record

    def get_qr_image(self, user_id: str, qr_id: str) -> bytes:
        """Regenerate the PNG for an existing QR code record.

        QR codes are deterministic: same redirect_url always produces the same image,
        so there is no need to store the image bytes — just regenerate on demand.
        """
        record = self.get_qr_record(user_id, qr_id)
        return self.qr_generator.generate(record.redirect_url)

    def resolve_redirect(self, qr_id: str) -> str:
        """
        The hot path. Must complete in < 100 ms end-to-end in production.
          In-memory dict : nanoseconds
          Redis GET       : ~0.5 ms
          PostgreSQL SELECT: ~5–20 ms  ← why we maintain a separate cache

        time.monotonic() is used here to show where you'd add metrics.
        In production: emit elapsed_ms to Prometheus/Datadog and alert
        if the p99 latency exceeds 100 ms.
        """
        start = time.monotonic()
        url = self.storage.resolve_redirect(qr_id)
        elapsed_ms = (time.monotonic() - start) * 1000

        if url is None:
            raise QRCodeNotFoundError(f"QR code '{qr_id}' not found.")

        print(f"[REDIRECT] {qr_id} → {url}  ({elapsed_ms:.3f} ms)")
        return url
