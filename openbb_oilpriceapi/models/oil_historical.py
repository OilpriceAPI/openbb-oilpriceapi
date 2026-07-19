"""OilPriceAPI Historical Price model and fetcher."""

from datetime import datetime
from math import isfinite
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
)
from openbb_oilpriceapi.models.oil_price import (
    AuthenticationError,
    OilPriceAPIFetcher,
    RateLimitError,
    ResponseSchemaError,
)


# Supported historical periods
HISTORICAL_PERIODS = ["past_day", "past_week", "past_month"]


class OilHistoricalQueryParams(QueryParams):
    """OilPriceAPI Historical Query Parameters.

    Source: https://docs.oilpriceapi.com
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
        description="Versioned OilPriceAPI historical period to request.",
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
    currency: str = Field(description="The API-provided price currency.")
    unit: str = Field(description="The API-provided unit of measurement.")
    source: str | None = Field(
        default=None, description="The API-provided source label, when available."
    )


class OilHistoricalFetcher(Fetcher[OilHistoricalQueryParams, list[OilHistoricalData]]):
    """OilPriceAPI Historical Price Fetcher."""

    require_credentials = True

    @staticmethod
    def transform_query(params: dict[str, Any]) -> OilHistoricalQueryParams:
        """Transform the query parameters."""
        return OilHistoricalQueryParams(**params)

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
                "Create or manage a key at https://www.oilpriceapi.com/auth/signup"
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
                data = await OilPriceAPIFetcher._fetch_with_retry(client, url, headers)
            except RateLimitError:
                raise RateLimitError(
                    "Rate limit exceeded after 3 retries. "
                    "Please wait before making more requests."
                )

            payload = data.get("data")
            records: Any = None
            if isinstance(payload, dict):
                records = payload.get("prices")
            elif isinstance(payload, list):
                records = payload

            if (
                not isinstance(records, list)
                or not records
                or not all(isinstance(record, dict) for record in records)
            ):
                raise ResponseSchemaError(
                    "OilPriceAPI returned no usable historical records in a successful response."
                )
            return records

    @staticmethod
    def transform_data(
        query: OilHistoricalQueryParams,
        data: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[OilHistoricalData]:
        """Transform API response to OilHistoricalData models."""
        if not data:
            raise ResponseSchemaError("OilPriceAPI returned no historical records.")

        results = []

        for item in data:
            if not isinstance(item, dict):
                raise ResponseSchemaError(
                    "OilPriceAPI returned a non-object historical record."
                )

            raw_code = item.get("code")
            if not isinstance(raw_code, str) or not raw_code.strip():
                raise ResponseSchemaError(
                    "OilPriceAPI historical record is missing its code."
                )
            try:
                price = float(item["price"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ResponseSchemaError(
                    f"OilPriceAPI historical record {raw_code} has no numeric price."
                ) from exc
            if not isfinite(price):
                raise ResponseSchemaError(
                    f"OilPriceAPI historical record {raw_code} has a non-finite price."
                )

            currency = item.get("currency")
            unit_value = item.get("unit")
            if not isinstance(currency, str) or not currency.strip():
                raise ResponseSchemaError(
                    f"OilPriceAPI historical record {raw_code} is missing currency."
                )
            if not isinstance(unit_value, str) or not unit_value.strip():
                raise ResponseSchemaError(
                    f"OilPriceAPI historical record {raw_code} is missing unit."
                )

            date_str = (
                item.get("created_at") or item.get("date") or item.get("timestamp")
            )
            if isinstance(date_str, datetime):
                date = date_str
            elif isinstance(date_str, str) and date_str.strip():
                try:
                    date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise ResponseSchemaError(
                        f"OilPriceAPI historical record {raw_code} has a malformed timestamp."
                    ) from exc
            else:
                raise ResponseSchemaError(
                    f"OilPriceAPI historical record {raw_code} is missing its timestamp."
                )

            # Get symbol from query (historical data is for specific symbol)
            symbol = query.symbol

            # Clean up unit string
            unit = unit_value.removeprefix("per ").strip()
            if not unit:
                raise ResponseSchemaError(
                    f"OilPriceAPI historical record {raw_code} has an empty unit."
                )

            results.append(
                OilHistoricalData(
                    date=date,
                    symbol=symbol,
                    price=price,
                    currency=currency,
                    unit=unit,
                    source=(
                        item.get("source")
                        if isinstance(item.get("source"), str)
                        else None
                    ),
                )
            )

        # Sort by date ascending
        results.sort(key=lambda x: x.date)

        return results
