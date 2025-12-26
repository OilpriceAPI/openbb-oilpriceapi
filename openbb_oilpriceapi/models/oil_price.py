"""OilPriceAPI Oil Price model and fetcher."""

from datetime import datetime
from typing import Any

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


class OilPriceAPIError(Exception):
    """Base exception for OilPriceAPI errors."""

    pass


class AuthenticationError(OilPriceAPIError):
    """Raised when API key is invalid or missing."""

    pass


class RateLimitError(OilPriceAPIError):
    """Raised when rate limit is exceeded."""

    pass


class NotFoundError(OilPriceAPIError):
    """Raised when commodity is not found."""

    pass


class OilPriceAPIQueryParams(QueryParams):
    """OilPriceAPI Query Parameters.

    Source: https://oilpriceapi.com
    """

    __json_schema_extra__ = {
        "symbol": {
            "multiple_items_allowed": False,
            "choices": AVAILABLE_SYMBOLS,
        }
    }

    symbol: str | None = Field(
        default=None,
        description="The commodity symbol to fetch. If None, returns all available commodities. "
        f"Available symbols: {', '.join(AVAILABLE_SYMBOLS)}",
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, v: str | None) -> str | None:
        """Validate that symbol is in the list of available symbols."""
        if v is None:
            return v
        v_upper = v.upper()
        if v_upper not in AVAILABLE_SYMBOLS:
            raise ValueError(
                f"Invalid symbol '{v}'. Available symbols: {', '.join(AVAILABLE_SYMBOLS)}"
            )
        return v_upper


class OilPriceAPIData(Data):
    """OilPriceAPI Oil Price Data Model."""

    symbol: str = Field(description="The commodity symbol/code.")
    name: str = Field(description="The commodity name.")
    price: float = Field(description="The current price.")
    currency: str = Field(description="The price currency (e.g., USD).")
    unit: str = Field(description="The unit of measurement (e.g., barrel, therm).")
    updated_at: datetime = Field(description="The timestamp of the last price update.")
    change: float | None = Field(
        default=None, description="The absolute price change."
    )
    change_percent: float | None = Field(
        default=None, description="The percentage price change."
    )


class OilPriceAPIFetcher(Fetcher[OilPriceAPIQueryParams, list[OilPriceAPIData]]):
    """OilPriceAPI Oil Price Fetcher."""

    require_credentials = True

    @staticmethod
    def transform_query(params: dict[str, Any]) -> OilPriceAPIQueryParams:
        """Transform the query parameters."""
        return OilPriceAPIQueryParams(**params)

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
        query: OilPriceAPIQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Extract data from OilPriceAPI."""
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Determine endpoint based on symbol
            if query.symbol:
                # Map OpenBB symbol to OilPriceAPI code
                oilpriceapi_code = SYMBOL_MAPPING.get(query.symbol, query.symbol)
                url = f"{OILPRICEAPI_BASE_URL}/prices/latest?by_code={oilpriceapi_code}"
            else:
                url = f"{OILPRICEAPI_BASE_URL}/prices/latest"

            try:
                data = await OilPriceAPIFetcher._fetch_with_retry(client, url, headers)
            except RateLimitError:
                # Re-raise with user-friendly message after retries exhausted
                raise RateLimitError(
                    "Rate limit exceeded after 3 retries. "
                    "Please wait before making more requests."
                )

            # Handle different response structures
            if "data" in data:
                if "prices" in data["data"]:
                    # Multiple prices response
                    return data["data"]["prices"]
                elif "price" in data["data"]:
                    # Single price response
                    return [data["data"]["price"]]
                else:
                    return [data["data"]]

            return []

    @staticmethod
    def transform_data(
        query: OilPriceAPIQueryParams,
        data: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[OilPriceAPIData]:
        """Transform API response to OilPriceAPIData models."""
        results = []

        for item in data:
            # Parse the timestamp
            updated_at_str = item.get("created_at") or item.get("updated_at")
            if updated_at_str:
                if isinstance(updated_at_str, str):
                    # Handle ISO format with or without Z suffix
                    updated_at_str = updated_at_str.replace("Z", "+00:00")
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str)
                    except ValueError:
                        updated_at = datetime.now()
                else:
                    updated_at = updated_at_str
            else:
                updated_at = datetime.now()

            # Get the symbol - use OpenBB symbol if available
            raw_symbol = item.get("code", item.get("symbol", "UNKNOWN"))
            symbol = REVERSE_SYMBOL_MAPPING.get(raw_symbol, raw_symbol)

            # Clean up unit string
            unit = item.get("unit", "").replace("per ", "").strip()

            results.append(
                OilPriceAPIData(
                    symbol=symbol,
                    name=item.get("name", ""),
                    price=float(item.get("price", 0)),
                    currency=item.get("currency", "USD"),
                    unit=unit or "barrel",
                    updated_at=updated_at,
                    change=item.get("change"),
                    change_percent=item.get("change_percent"),
                )
            )

        return results
