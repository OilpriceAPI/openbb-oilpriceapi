"""OilPriceAPI Oil Price model and fetcher."""

from datetime import datetime
from typing import Any, Literal

import httpx
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from openbb_core.provider.abstract.data import Data
from pydantic import Field, field_validator

from openbb_oilpriceapi.utils.constants import (
    SYMBOL_MAPPING,
    AVAILABLE_SYMBOLS,
    OILPRICEAPI_BASE_URL,
    REVERSE_SYMBOL_MAPPING,
)


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


class OilPriceAPIFetcher(
    Fetcher[OilPriceAPIQueryParams, list[OilPriceAPIData]]
):
    """OilPriceAPI Oil Price Fetcher."""

    require_credentials = True

    @staticmethod
    def transform_query(params: dict[str, Any]) -> OilPriceAPIQueryParams:
        """Transform the query parameters."""
        return OilPriceAPIQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: OilPriceAPIQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Extract data from OilPriceAPI."""
        api_key = credentials.get("api_key") if credentials else None
        if not api_key:
            raise ValueError(
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

            response = await client.get(url, headers=headers)

            if response.status_code == 401:
                raise ValueError("Invalid API key. Check your OilPriceAPI credentials.")
            if response.status_code == 429:
                raise ValueError(
                    "Rate limit exceeded. Please wait before making more requests."
                )
            if response.status_code == 404:
                raise ValueError(f"Commodity not found: {query.symbol}")

            response.raise_for_status()

            data = response.json()

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
