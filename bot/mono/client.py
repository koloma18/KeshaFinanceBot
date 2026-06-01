import asyncio
import time

import httpx
from config import MONOBANK_X_TOKEN

BASE_URL = "https://api.monobank.ua"
REQUEST_INTERVAL = 0  # client-side throttle disabled, server-side 429 handles it
REQUEST_TIMEOUT = 10  # seconds per request
MAX_RETRIES = 3


class MonobankError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


def _convert_amount(amount: int, currency_code: int) -> float:
    """Convert minor units (kopecks/cents) to major units.

    Currency codes: 980 = UAH, 840 = USD, 978 = EUR.
    All Monobank amounts are in minor units (÷100).
    """
    return amount / 100.0


_CURRENCY_MAP = {
    980: "UAH",
    840: "USD",
    978: "EUR",
}


def currency_code_to_name(code: int) -> str:
    """Map ISO 4217 numeric currency code to short name."""
    return _CURRENCY_MAP.get(code, f"CC{code}")


class MonobankClient:
    """Async Monobank API client with global rate limiting and error handling."""

    _last_request_time: float = 0.0  # class-level: shared across all instances

    def __init__(self, token: str | None = None):
        self._token = token or MONOBANK_X_TOKEN
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=httpx.Timeout(REQUEST_TIMEOUT),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_client_info(self) -> dict:
        """GET /personal/client-info — client profile and account list."""
        return await self._request("GET", "/personal/client-info")

    async def get_statement(
        self, account_id: str, from_ts: int, to_ts: int
    ) -> list[dict]:
        """GET /personal/statement/{account}/{from}/{to}.

        Args:
            account_id: Monobank account ID.
            from_ts: Unix timestamp (seconds), start of period.
            to_ts: Unix timestamp (seconds), end of period.

        Max date range: 31 days + 1 hour between from_ts and to_ts.
        Amounts are returned in minor units (kopecks/cents).
        Returns raw list with amount in kopecks — caller converts.
        """
        path = f"/personal/statement/{account_id}/{from_ts}/{to_ts}"
        return await self._request("GET", path)

    async def set_webhook(self, url: str) -> dict:
        """POST /personal/webhook — set webhook URL for real-time updates."""
        return await self._request(
            "POST", "/personal/webhook", json_data={"webHookUrl": url}
        )

    async def get_currency_rates(self) -> list[dict]:
        """GET /bank/currency — public exchange rates (no token needed)."""
        return await self._request("GET", "/bank/currency", use_token=False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        use_token: bool = True,
    ) -> dict | list:
        """Make a rate-limited, error-handled request to Monobank API."""
        await self._rate_limit()

        headers = {}
        if use_token and self._token:
            headers["X-Token"] = self._token

        attempt = 0
        while attempt <= MAX_RETRIES:
            attempt += 1

            try:
                response = await self._client.request(
                    method=method,
                    url=path,
                    headers=headers,
                    json=json_data,
                )
            except httpx.TimeoutException:
                if attempt > MAX_RETRIES:
                    raise MonobankError(0, "Request timed out after multiple retries")
                await asyncio.sleep(2**attempt)
                continue
            except httpx.RequestError as exc:
                raise MonobankError(0, f"Network error: {exc}")

            # Success
            if response.is_success:
                MonobankClient._last_request_time = time.monotonic()
                return response.json()

            # 429 Too Many Requests — backoff
            if response.status_code == 429:
                retry_after = _parse_retry_after(response)
                if attempt > MAX_RETRIES:
                    raise MonobankError(
                        429, f"Rate limited, gave up after {MAX_RETRIES} retries"
                    )
                await asyncio.sleep(retry_after)
                continue

            # Other HTTP errors
            self._last_request_time = time.monotonic()
            try:
                body = response.json()
                err_msg = body.get("errorDescription", str(body))
            except Exception:
                err_msg = response.text or "Unknown error"
            raise MonobankError(response.status_code, err_msg)

        # Should not reach here
        raise MonobankError(0, "Unexpected error in _request")

    async def _rate_limit(self) -> None:
        """Ensure at least REQUEST_INTERVAL seconds between requests (global)."""
        elapsed = time.monotonic() - MonobankClient._last_request_time
        if elapsed < REQUEST_INTERVAL:
            await asyncio.sleep(REQUEST_INTERVAL - elapsed)


def _parse_retry_after(response: httpx.Response) -> float:
    """Extract Retry-After header as seconds, with fallback."""
    raw = response.headers.get("Retry-After", "")
    if raw.isdigit():
        return float(raw)
    # If it's a HTTP-date, fall back to a reasonable wait
    return 5.0
