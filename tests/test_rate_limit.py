"""429 handling: durable quota errors fail fast, short burst limits honor Retry-After."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from openbb_oilpriceapi.models.oil_historical import (
    OilHistoricalFetcher,
    OilHistoricalQueryParams,
)
from openbb_oilpriceapi.models.oil_price import (
    AuthenticationError,
    EntitlementError,
    MAX_RETRY_WAIT_SECONDS,
    OilPriceAPIFetcher,
    OilPriceAPIQueryParams,
    RateLimitError,
    parse_retry_after,
)

URL = "https://api.oilpriceapi.com/v1/prices/latest?by_code=WTI_USD"
OK_BODY = {
    "status": "success",
    "data": {
        "code": "WTI_USD",
        "price": 61.2,
        "currency": "USD",
        "unit": "barrel",
        "created_at": "2026-10-03T20:00:00Z",
    },
}


def _response(status, body=None, retry_after=None):
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return httpx.Response(
        status,
        json=body if body is not None else {},
        headers=headers,
        request=httpx.Request("GET", URL),
    )


def _client(*responses):
    client = AsyncMock()
    client.get.side_effect = list(responses)
    return client


class FakeSleep:
    def __init__(self):
        self.calls = []

    async def __call__(self, seconds):
        self.calls.append(seconds)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    [
        "MONTHLY_QUOTA_EXCEEDED",
        "TRIAL_EXPIRED",
        "TRIAL_LIMIT_EXCEEDED",
        "EMAIL_CONFIRMATION_REQUIRED",
        "RATE_LIMIT_EXCEEDED",
    ],
)
async def test_durable_quota_makes_one_request_and_reports_recovery(code):
    body = {
        "error_code": code,
        "message": "You've used all 200 requests for Free tier today",
        "upgrade_url": "https://www.oilpriceapi.com/pricing",
    }
    client = _client(_response(429, body, retry_after="5"))
    sleep = FakeSleep()

    with pytest.raises(RateLimitError) as info:
        await OilPriceAPIFetcher._fetch_with_retry(client, URL, {}, sleep=sleep)

    assert client.get.await_count == 1
    assert sleep.calls == []
    err = info.value
    assert err.durable
    assert err.error_code == code
    assert err.retry_after == 5.0
    assert code in str(err)
    assert "used all 200 requests" in str(err)
    assert "https://www.oilpriceapi.com/pricing" in str(err)


@pytest.mark.asyncio
async def test_burst_limit_honors_delta_seconds_then_succeeds():
    client = _client(
        _response(429, {"error_code": "HOURLY_CIRCUIT_BREAKER_EXCEEDED"}, "3"),
        _response(200, OK_BODY),
    )
    sleep = FakeSleep()

    data = await OilPriceAPIFetcher._fetch_with_retry(client, URL, {}, sleep=sleep)

    assert data == OK_BODY
    assert client.get.await_count == 2
    assert sleep.calls == [3.0]


@pytest.mark.asyncio
async def test_burst_limit_honors_http_date():
    fixed_now = datetime(2026, 10, 3, 20, 0, 0, tzinfo=timezone.utc)
    assert parse_retry_after("Sat, 03 Oct 2026 20:00:07 GMT", now=fixed_now) == 7.0
    assert parse_retry_after("Sat, 03 Oct 2026 19:59:00 GMT", now=fixed_now) == 0.0


@pytest.mark.asyncio
async def test_retry_after_beyond_budget_raises_promptly():
    too_long = str(int(MAX_RETRY_WAIT_SECONDS) + 1)
    client = _client(
        _response(429, {"error_code": "HOURLY_CIRCUIT_BREAKER_EXCEEDED"}, too_long)
    )
    sleep = FakeSleep()

    with pytest.raises(RateLimitError) as info:
        await OilPriceAPIFetcher._fetch_with_retry(client, URL, {}, sleep=sleep)

    assert client.get.await_count == 1
    assert sleep.calls == []
    assert info.value.retry_after == float(too_long)
    assert f"Retry after {too_long} seconds" in str(info.value)


@pytest.mark.asyncio
async def test_malformed_retry_after_is_not_guessed():
    client = _client(
        _response(429, {"error_code": "HOURLY_CIRCUIT_BREAKER_EXCEEDED"}, "soon")
    )
    sleep = FakeSleep()

    with pytest.raises(RateLimitError):
        await OilPriceAPIFetcher._fetch_with_retry(client, URL, {}, sleep=sleep)

    assert client.get.await_count == 1
    assert sleep.calls == []


@pytest.mark.asyncio
async def test_missing_retry_after_uses_bounded_backoff_and_caps_attempts():
    client = _client(
        _response(429, {"error_code": "RATE_LIMIT_CHECK_FAILED"}),
        _response(429, {"error_code": "RATE_LIMIT_CHECK_FAILED"}),
        _response(429, {"error_code": "RATE_LIMIT_CHECK_FAILED"}),
    )
    sleep = FakeSleep()

    with pytest.raises(RateLimitError) as info:
        await OilPriceAPIFetcher._fetch_with_retry(client, URL, {}, sleep=sleep)

    assert client.get.await_count == 3
    assert sleep.calls == [1.0, 2.0]
    assert not info.value.durable


@pytest.mark.asyncio
async def test_429_with_non_json_body_is_handled():
    response = httpx.Response(
        429, text="Too Many Requests", request=httpx.Request("GET", URL)
    )
    client = _client(response, _response(200, OK_BODY))
    sleep = FakeSleep()

    data = await OilPriceAPIFetcher._fetch_with_retry(client, URL, {}, sleep=sleep)

    assert data == OK_BODY
    assert sleep.calls == [1.0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,error",
    [(401, AuthenticationError), (402, EntitlementError), (403, EntitlementError)],
)
async def test_auth_and_entitlement_errors_are_not_retried(status, error):
    client = _client(_response(status, {"error_code": "X"}, "1"))
    sleep = FakeSleep()

    with pytest.raises(error):
        await OilPriceAPIFetcher._fetch_with_retry(client, URL, {}, sleep=sleep)

    assert client.get.await_count == 1
    assert sleep.calls == []


def _patched_client(response):
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


@pytest.mark.asyncio
async def test_latest_surfaces_durable_quota_without_retrying():
    client = _patched_client(_response(429, {"error_code": "MONTHLY_QUOTA_EXCEEDED"}))

    with (
        patch("httpx.AsyncClient", return_value=client),
        pytest.raises(RateLimitError, match="MONTHLY_QUOTA_EXCEEDED"),
    ):
        await OilPriceAPIFetcher.aextract_data(
            OilPriceAPIQueryParams(symbol="WTI"), {"api_key": "test_key"}
        )

    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_historical_surfaces_durable_quota_without_retrying():
    client = _patched_client(_response(429, {"error_code": "TRIAL_EXPIRED"}))

    with (
        patch("httpx.AsyncClient", return_value=client),
        pytest.raises(RateLimitError, match="TRIAL_EXPIRED"),
    ):
        await OilHistoricalFetcher.aextract_data(
            OilHistoricalQueryParams(symbol="WTI"), {"api_key": "test_key"}
        )

    assert client.get.await_count == 1


def test_rate_limit_error_still_constructs_from_message_only():
    err = RateLimitError("Rate limit exceeded")
    assert str(err) == "Rate limit exceeded"
    assert not err.durable
    assert err.retry_after is None


def test_parse_retry_after_rejects_garbage():
    assert parse_retry_after(None) is None
    assert parse_retry_after("") is None
    assert parse_retry_after("-5") is None
    assert parse_retry_after("1.5") is None
    assert parse_retry_after("tomorrow") is None


def test_response_without_headers_attribute_is_tolerated():
    response = MagicMock(status_code=429)
    response.json.return_value = {"error_code": "MONTHLY_QUOTA_EXCEEDED"}
    del response.headers
    err = RateLimitError.from_response(response)
    assert err.durable
    assert err.retry_after is None
