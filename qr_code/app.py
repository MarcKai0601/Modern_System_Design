"""
FastAPI application: route handlers for the QR Code service.
"""

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse, RedirectResponse

from .models import DuplicateURLError, QRCodeNotFoundError, URLValidationError, UserNotFoundError
from .service import QRCodeGenerator, QRCodeService
from .storage import InMemoryStorage

app = FastAPI(
    title="QR Code Generator",
    description="System design learning project: URL → QR Code service",
    version="1.0.0",
)

# Module-level singletons — dependency injection at module scope.
# In production: use FastAPI's Depends() system so each layer can be
# independently mocked in tests.
_storage = InMemoryStorage()
_qr_generator = QRCodeGenerator()
_service = QRCodeService(_storage, _qr_generator)


@app.post(
    "/api/users/{user_id}/qr-codes",
    status_code=201,
    summary="Create a QR code for a URL",
    response_class=Response,
)
def create_qr_code(user_id: str, url: str) -> Response:
    """
    Submit a URL (ASCII, max 20 chars) and receive a PNG QR code image.

    - **201 Created**: PNG image returned in the body.
    - **409 Conflict**: you already have a QR code for this URL.
    - **422 Unprocessable Entity**: URL fails validation.
    """
    try:
        record, image_bytes = _service.create_qr_code(user_id, url)
    except URLValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except DuplicateURLError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return Response(
        content=image_bytes,
        media_type="image/png",
        status_code=201,
        headers={"Content-Disposition": f'attachment; filename="{record.qr_id}.png"'},
    )


@app.get(
    "/api/users/{user_id}/qr-codes",
    status_code=200,
    summary="List all QR codes for a user",
)
def list_qr_codes(user_id: str) -> JSONResponse:
    """
    Returns JSON metadata for all QR codes owned by this user (no images).

    - **200 OK**: JSON array (may be empty if no QR codes yet).
    - **404 Not Found**: user_id is unknown (user must POST first to exist).
    """
    try:
        records = _service.list_qr_codes(user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    payload = [
        {
            "qr_id": r.qr_id,
            "original_url": r.original_url,
            "redirect_url": r.redirect_url,
            "created_at": r.created_at.isoformat(),
            "scan_count": r.scan_count,
        }
        for r in records
    ]
    return JSONResponse(content=payload)


@app.delete(
    "/api/users/{user_id}/qr-codes/{qr_id}",
    status_code=204,
    summary="Delete a QR code",
)
def delete_qr_code(user_id: str, qr_id: str) -> Response:
    """
    Permanently removes the QR code. Scanning it afterwards returns 404.

    - **204 No Content**: deleted successfully (body-less; REST convention for DELETE).
    - **404 Not Found**: user or QR code not found.

    Security: returns 404 (not 403) when the qr_id belongs to a different user,
    to avoid leaking the existence of other users' QR codes.
    """
    try:
        _service.delete_qr_code(user_id, qr_id)
    except (UserNotFoundError, QRCodeNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(status_code=204)


@app.get(
    "/{qr_id}",
    summary="Scan QR code — redirects to the original URL",
    response_class=RedirectResponse,
)
def redirect_to_url(qr_id: str) -> RedirectResponse:
    """
    **THE HOT PATH.** This endpoint must respond in < 100 ms end-to-end.

    Why is this at the ROOT path (not `/api/redirect/{qr_id}`)?
    Every character in the URL embedded in the QR code adds modules to
    the QR matrix, making it harder to scan. A root-path URL is as short
    as possible, producing the smallest, most scannable QR code.

    Why HTTP 307 (not 301)?
    - **301 Permanent**: browsers cache the redirect forever. If the destination
      URL ever needs to change, cached browsers will never re-check the server.
    - **307 Temporary**: browsers always ask the server. Every scan is visible
      for analytics, and the destination URL can be updated in the future.
    """
    try:
        original_url = _service.resolve_redirect(qr_id)
    except QRCodeNotFoundError:
        raise HTTPException(status_code=404, detail=f"QR code '{qr_id}' not found.")

    return RedirectResponse(url=original_url, status_code=307)
