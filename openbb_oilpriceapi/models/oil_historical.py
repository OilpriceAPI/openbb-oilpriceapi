"""OilPriceAPI Historical Price model and fetcher."""

from datetime import datetime
from typing import Any, Literal

import httpx
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from openbb_core.provider.abstract.data import Data
from pydantic import Field, field_validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from openbb_oilpriceapi.utils.constants import (
    SYMBOL_MAPPING,
    AVAILABLE_SYMBOLS,
    OILPRICEAPI_BASE_URL,
    REVERSE_SYMBOL_MAPPING,
)
from openbb_oilpriceapi.models.oil_price import (
    AuthenticationError,
    RateLimitError,
    NotFoundError,
)


# Supported historical periods
HISTORICAL_PERIODS = ["past_day", "past_week", "past_month"]


class OilHistoricalQueryParams(QueryParams):
    """OilPriceAPI Historical Query Parameters.

    Source: https://oilpriceapi.com
    """

    __json_schema_extra__ = {
        "symbol": {
            "multiple_items_allowed": False,
            "choices": AVAILABLE_SYMBOLS,
        },
        "period": {
            "multiple_items_allowed": False,
            "choices": HISTORICAL_PERIODS,
        },
    }

    symbol: str = Field(
        description="The commodity symbol to fetch historical data for. "
        f"Available symbols: {', '.join(AVAILABLE_SYMBOLS)}",
    )
    period: Literal["past_day", "past_week", "past_month"] = Field(
        default="past_week",
        description="Historical period: past_day (24h hourly), past_week (7d daily), past_month (30d daily).",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate that symbol is in the list of available symbols."""
        v_upper = v.upper()
        if v_upper not in AVAILABLE_SYMBOLS:
            raise ValueError(
                f"Invalid symbol '{v}'. Available symbols: {', '.join(AVAILABLE_SYMBOLS)}"
            )
        return v_upper


class OilHistoricalData(Data):
    """OilPriceAPI Historical Price Data Model."""

    date: datetime = Field(description="The timestamp of the price data point.")
    symbol: str = Field(description="The commodity symbol/code.")
    price: float = Field(description="The price at this timestamp.")
    currency: str = Field(default="USD", description="The price currency.")
    unit: str = Field(default="barrel", description="The unit of measurement.")


class OilHistoricalFetcher(Fetcher[OilHistoricalQueryParams, list[OilHistoricalData]]):
    """OilPriceAPI Historical Price Fetcher."""

    require_credentials = True

    @staticmethod
    def transform_query(params: dict[str, Any]) -> OilHistoricalQueryParams:
        """Transform the query parameters."""
        return OilHistoricalQueryParams(**params)

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    async def _fetch_with_retry(
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Fetch data with retry logic for rate limits."""
        response = await client.get(url, headers=headers)

        if response.status_code == 401:
            raise AuthenticationError(
                "Invalid API key. Check your OilPriceAPI credentials."
            )
        if response.status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded. Retrying with exponential backoff..."
            )
        if response.status_code == 404:
            raise NotFoundError("Commodity not found.")

        response.raise_for_status()
        return response.json()

    @staticmethod
    async def aextract_data(
        query: OilHistoricalQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Extract historical data from OilPriceAPI."""
        api_key = credentials.get("api_key") if credentials else None
        if not api_key:
            raise AuthenticationError(
                "OilPriceAPI API key is required. "
                "Get a free key at https://oilpriceapi.com"
            )

        headers = {
            "Authorization": f"Token {api_key}",
            "Accept": "application/json",
        }

        # Map OpenBB symbol to OilPriceAPI code
        oilpriceapi_code = SYMBOL_MAPPING.get(query.symbol, query.symbol)
        url = f"{OILPRICEAPI_BASE_URL}/prices/{query.period}?by_code={oilpriceapi_code}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                data = await OilHistoricalFetcher._fetch_with_retry(
                    client, url, headers
                )
            except RateLimitError:
                raise RateLimitError(
                    "Rate limit exceeded after 3 retries. "
                    "Please wait before making more requests."
                )

            # Handle response structure
            if "data" in data:
                if "prices" in data["data"]:
                    return data["data"]["prices"]
                elif isinstance(data["data"], list):
                    return data["data"]

            return []

    @staticmethod
    def transform_data(
        query: OilHistoricalQueryParams,
        data: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[OilHistoricalData]:
        """Transform API response to OilHistoricalData models."""
        results = []

        for item in data:
            # Parse the timestamp
            date_str = item.get("created_at") or item.get("date") or item.get("timestamp")
            if date_str:
                if isinstance(date_str, str):
                    date_str = date_str.replace("Z", "+00:00")
                    try:
                        date = datetime.fromisoformat(date_str)
                    except ValueError:
                        continue  # Skip invalid dates
                else:
                    date = date_str
            else:
                continue  # Skip entries without dates

            # Get symbol from query (historical data is for specific symbol)
            symbol = query.symbol

            # Clean up unit string
            unit = item.get("unit", "").replace("per ", "").strip() or "barrel"

            results.append(
                OilHistoricalData(
                    date=date,
                    symbol=symbol,
                    price=float(item.get("price", 0)),
                    currency=item.get("currency", "USD"),
                    unit=unit,
                )
            )

        # Sort by date ascending
        results.sort(key=lambda x: x.date)

        return results
