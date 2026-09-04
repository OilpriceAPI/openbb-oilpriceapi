"""Regression tests for server-visible, secret-safe SDK attribution."""

from importlib.metadata import version
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openbb_oilpriceapi.models.oil_historical import (
    OilHistoricalFetcher,
    OilHistoricalQueryParams,
)
from openbb_oilpriceapi.models.oil_price import (
    OilPriceAPIFetcher,
    OilPriceAPIQueryParams,
)
from openbb_oilpriceapi.utils.telemetry import SDK_NAME, SDK_VERSION


EXPECTED_ATTRIBUTION = {
    "User-Agent": f"oilpriceapi-openbb/{SDK_VERSION}",
    "X-SDK-Name": "oilpriceapi-openbb",
    "X-SDK-Version": SDK_VERSION,
    "X-SDK-Language": "python",
    "X-Client-Type": "sdk",
}


def _successful_response() -> MagicMock:
    response = MagicMock(status_code=200)
    response.json.return_value = {
        "data": {
            "prices": [
                {
                    "code": "WTI_USD",
                    "price": 72.5,
                    "currency": "USD",
                    "unit": "per barrel",
                    "created_at": "2026-09-04T12:00:00Z",
                }
            ]
        }
    }
    return response


async def _captured_headers(
    fetcher: type, query: object, secret: str
) -> dict[str, str]:
    with patch("httpx.AsyncClient") as mock_client:
        client = AsyncMock()
        client.get.return_value = _successful_response()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        mock_client.return_value = client

        await fetcher.aextract_data(query, {"api_key": secret})

    return client.get.call_args.kwargs["headers"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fetcher", "query"),
    [
        (OilPriceAPIFetcher, OilPriceAPIQueryParams(symbol="WTI")),
        (
            OilHistoricalFetcher,
            OilHistoricalQueryParams(symbol="WTI", period="past_year"),
        ),
    ],
)
async def test_all_request_paths_send_canonical_secret_safe_attribution(
    fetcher: type, query: object
) -> None:
    secret = "opa_test_secret_must_not_leak"
    headers = await _captured_headers(fetcher, query, secret)

    for name, value in EXPECTED_ATTRIBUTION.items():
        assert headers[name] == value
        assert secret not in value
    assert headers["Authorization"] == f"Token {secret}"


def test_attribution_version_is_the_installed_distribution_version() -> None:
    assert SDK_NAME == "oilpriceapi-openbb"
    assert SDK_VERSION == version("openbb-oilpriceapi") == "0.3.0"
