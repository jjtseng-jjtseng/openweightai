import hmac
import os

from fastapi import HTTPException, Request, status


def _configured_api_key() -> str | None:
    key = os.getenv("API_KEY", "").strip()
    return key or None


async def require_api_key(request: Request) -> None:
    """Require an API key only when API_KEY is configured."""
    expected = _configured_api_key()
    if expected is None:
        return

    supplied = request.headers.get("x-api-key", "").strip()
    auth_header = request.headers.get("authorization", "").strip()
    if not supplied and auth_header.lower().startswith("bearer "):
        supplied = auth_header[7:].strip()

    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )

