"""OilPriceAPI Oil Price model and fetcher."""

from datetime import datetime
from math import isfinite
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


class EntitlementError(OilPriceAPIError):
    """Raised when the account cannot access the requested dataset."""

    pass


class ProviderTimeoutError(OilPriceAPIError):
    """Raised when OilPriceAPI does not respond within the provider timeout."""

    pass


class ResponseSchemaError(OilPriceAPIError):
    """Raised when a successful response has no usable source data."""

    pass


class NotFoundError(OilPriceAPIError):
    """Raised when commodity is not found."""

    pass


class OilPriceAPIQueryParams(QueryParams):
    """OilPriceAPI Query Parameters.

    Source: https://docs.oilpriceapi.com
    """

    __json_schema_extra__ = {
        "symbol": {
            "multiple_items_allowed": False,
            "choices": AVAILABLE_SYMBOLS,
        }
    }

    symbol: str | None = Field(
        default=None,
        description="The commodity symbol to fetch. If None, returns the API default latest record. "
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
    source: str | None = Field(
        default=None, description="The API-provided source label, when available."
    )
    change: float | None = Field(default=None, description="The absolute price change.")
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
        try:
            response = await client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                "OilPriceAPI request timed out. Retry later or reduce the requested scope."
            ) from exc

        if response.status_code == 401:
            raise AuthenticationError(
                "Invalid API key. Check your OilPriceAPI credentials."
            )
        if response.status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded. Retrying with exponential backoff..."
            )
        if response.status_code in (402, 403):
            raise EntitlementError(
                "This account cannot access the requested dataset. "
                "Review https://www.oilpriceapi.com/pricing"
            )
        if response.status_code == 404:
            raise NotFoundError("Commodity not found.")

        response.raise_for_status()
        try:
            data = response.json()
        except (TypeError, ValueError) as exc:
            raise ResponseSchemaError(
                "OilPriceAPI returned malformed JSON for a successful request."
            ) from exc
        if not isinstance(data, dict):
            raise ResponseSchemaError(
                "OilPriceAPI returned a non-object response for a successful request."
            )
        return data

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
                "Create or manage a key at https://www.oilpriceapi.com/auth/signup"
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

            payload = data.get("data")
            records: Any = None
            if isinstance(payload, dict):
                if "prices" in payload:
                    records = payload["prices"]
                elif isinstance(payload.get("price"), dict):
                    records = [payload["price"]]
                elif "code" in payload or "price" in payload:
                    records = [payload]
            elif isinstance(payload, list):
                records = payload

            if (
                not isinstance(records, list)
                or not records
                or not all(isinstance(record, dict) for record in records)
            ):
                raise ResponseSchemaError(
                    "OilPriceAPI returned no usable price in a successful response."
                )
            return records

    @staticmethod
    def transform_data(
        query: OilPriceAPIQueryParams,
        data: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[OilPriceAPIData]:
        """Transform API response to OilPriceAPIData models."""
        if not data:
            raise ResponseSchemaError("OilPriceAPI returned no price records.")

        results = []

        for item in data:
            if not isinstance(item, dict):
                raise ResponseSchemaError(
                    "OilPriceAPI returned a non-object price record."
                )

            raw_symbol = item.get("code") or item.get("symbol")
            if not isinstance(raw_symbol, str) or not raw_symbol.strip():
                raise ResponseSchemaError(
                    "OilPriceAPI price record is missing its code."
                )

            try:
                price = float(item["price"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ResponseSchemaError(
                    f"OilPriceAPI price record {raw_symbol} has no numeric price."
                ) from exc
            if not isfinite(price):
                raise ResponseSchemaError(
                    f"OilPriceAPI price record {raw_symbol} has a non-finite price."
                )

            currency = item.get("currency")
            unit_value = item.get("unit")
            if not isinstance(currency, str) or not currency.strip():
                raise ResponseSchemaError(
                    f"OilPriceAPI price record {raw_symbol} is missing currency."
                )
            if not isinstance(unit_value, str) or not unit_value.strip():
                raise ResponseSchemaError(
                    f"OilPriceAPI price record {raw_symbol} is missing unit."
                )

            updated_at_str = item.get("created_at") or item.get("updated_at")
            if isinstance(updated_at_str, datetime):
                updated_at = updated_at_str
            elif isinstance(updated_at_str, str) and updated_at_str.strip():
                try:
                    updated_at = datetime.fromisoformat(
                        updated_at_str.replace("Z", "+00:00")
                    )
                except ValueError as exc:
                    raise ResponseSchemaError(
                        f"OilPriceAPI price record {raw_symbol} has a malformed timestamp."
                    ) from exc
            else:
                raise ResponseSchemaError(
                    f"OilPriceAPI price record {raw_symbol} is missing its timestamp."
                )

            # Get the symbol - use OpenBB symbol if available
            symbol = REVERSE_SYMBOL_MAPPING.get(raw_symbol, raw_symbol)

            # Clean up unit string
            unit = unit_value.removeprefix("per ").strip()
            if not unit:
                raise ResponseSchemaError(
                    f"OilPriceAPI price record {raw_symbol} has an empty unit."
                )

            results.append(
                OilPriceAPIData(
                    symbol=symbol,
                    name=item.get("name") or raw_symbol,
                    price=price,
                    currency=currency,
                    unit=unit,
                    updated_at=updated_at,
                    source=(
                        item.get("source")
                        if isinstance(item.get("source"), str)
                        else None
                    ),
                    change=item.get("change"),
                    change_percent=item.get("change_percent"),
                )
            )

        return results
