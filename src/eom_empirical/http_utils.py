"""Small, safe retry layer for public-data GET requests.

Retries bounded network failures and transient HTTP responses. TLS certificate
verification remains enabled; certificate errors are surfaced immediately rather
than bypassed or retried as if they were DNS failures.
"""
from __future__ import annotations

import time
from typing import Any

import requests

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_with_retries(
    url: str,
    *,
    session: requests.Session | None = None,
    timeout: float | tuple[float, float] = (10, 45),
    attempts: int = 4,
    base_delay: float = 0.75,
    max_delay: float = 12.0,
    **kwargs: Any,
) -> requests.Response:
    """GET a URL with bounded exponential backoff for transient network errors.

    If *session* is omitted, a short-lived Session is created and closed here.
    HTTP status retries are handled explicitly so callers receive the final
    response (and can record its status/body) if all attempts fail.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("retry delays must be >= 0")

    owns_session = session is None
    client = session or requests.Session()
    last_error: BaseException | None = None
    try:
        for attempt in range(attempts):
            try:
                response = client.get(url, timeout=timeout, **kwargs)
                if response.status_code in RETRYABLE_STATUS_CODES and attempt + 1 < attempts:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        delay = min(max(float(retry_after), 0.0), max_delay)
                    except (TypeError, ValueError):
                        delay = min(base_delay * (2**attempt), max_delay)
                    response.close()
                    if delay:
                        time.sleep(delay)
                    continue
                return response
            except requests.exceptions.SSLError:
                # Never turn off TLS verification or disguise certificate failures
                # as transient DNS outages.
                raise
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    raise
                delay = min(base_delay * (2**attempt), max_delay)
                if delay:
                    time.sleep(delay)

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"GET retry loop ended without a response for {url}")
    finally:
        if owns_session:
            client.close()
