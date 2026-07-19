"""Tests for OilPriceAPI oil price fetcher."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from tenacity import wait_none


class TestOilPriceQueryParams:
    """Test cases for OilPriceQueryParams data model."""

    def test_default_params(self):
        """Test default query parameters."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIQueryParams

        params = OilPriceAPIQueryParams()
        assert params.symbol is None  # All commodities by default

    def test_symbol_param(self):
        """Test symbol query parameter."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIQueryParams

        params = OilPriceAPIQueryParams(symbol="WTI")
        assert params.symbol == "WTI"

    def test_symbol_case_insensitive(self):
        """Test that symbol is case-insensitive."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIQueryParams

        params = OilPriceAPIQueryParams(symbol="wti")
        assert params.symbol == "WTI"

    def test_invalid_symbol_raises(self):
        """Test that invalid symbol raises validation error."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIQueryParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OilPriceAPIQueryParams(symbol="INVALID_COMMODITY_XYZ")


class TestOilPriceData:
    """Test cases for OilPriceData data model."""

    def test_data_model_fields(self):
        """Test that data model has required fields."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIData

        data = OilPriceAPIData(
            symbol="WTI",
            name="WTI Crude Oil",
            price=72.50,
            currency="USD",
            unit="barrel",
            updated_at=datetime.now(),
        )
        assert data.symbol == "WTI"
        assert data.price == 72.50
        assert data.currency == "USD"

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIData

        data = OilPriceAPIData(
            symbol="WTI",
            name="WTI Crude Oil",
            price=72.50,
            currency="USD",
            unit="barrel",
            updated_at=datetime.now(),
            change=0.50,
            change_percent=0.69,
        )
        assert data.change == 0.50
        assert data.change_percent == 0.69

    def test_optional_fields_none(self):
        """Test that optional fields can be None."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIData

        data = OilPriceAPIData(
            symbol="WTI",
            name="WTI Crude Oil",
            price=72.50,
            currency="USD",
            unit="barrel",
            updated_at=datetime.now(),
        )
        assert data.change is None
        assert data.change_percent is None


class TestOilPriceFetcher:
    """Test cases for OilPriceFetcher."""

    @pytest.fixture
    def mock_api_response_multiple(self):
        """Mock API response with multiple prices."""
        return {
            "data": {
                "prices": [
                    {
                        "code": "WTI_USD",
                        "name": "WTI Crude Oil",
                        "price": 72.50,
                        "currency": "USD",
                        "unit": "per barrel",
                        "created_at": "2025-12-26T12:00:00Z",
                        "change": 0.50,
                        "change_percent": 0.69,
                    },
                    {
                        "code": "BRENT_CRUDE_USD",
                        "name": "Brent Crude Oil",
                        "price": 76.25,
                        "currency": "USD",
                        "unit": "per barrel",
                        "created_at": "2025-12-26T12:00:00Z",
                        "change": -0.25,
                        "change_percent": -0.33,
                    },
                ]
            }
        }

    @pytest.fixture
    def mock_api_response_single(self):
        """Mock API response with single price."""
        return {
            "data": {
                "price": {
                    "code": "WTI_USD",
                    "name": "WTI Crude Oil",
                    "price": 72.50,
                    "currency": "USD",
                    "unit": "per barrel",
                    "created_at": "2025-12-26T12:00:00Z",
                    "change": 0.50,
                    "change_percent": 0.69,
                }
            }
        }

    def test_transform_query(self):
        """Test query transformation."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIFetcher

        params = {"symbol": "WTI"}
        query = OilPriceAPIFetcher.transform_query(params)
        assert query.symbol == "WTI"

    def test_transform_query_empty(self):
        """Test query transformation with empty params."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIFetcher

        params = {}
        query = OilPriceAPIFetcher.transform_query(params)
        assert query.symbol is None

    def test_transform_data(self, mock_api_response_multiple):
        """Test data transformation."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            OilPriceAPIData,
        )

        query = OilPriceAPIQueryParams()
        data = mock_api_response_multiple["data"]["prices"]
        result = OilPriceAPIFetcher.transform_data(query, data)

        assert len(result) == 2
        assert isinstance(result[0], OilPriceAPIData)
        assert result[0].symbol == "WTI"  # Mapped from WTI_USD
        assert result[0].price == 72.50
        assert result[1].symbol == "BRENT"  # Mapped from BRENT_CRUDE_USD
        assert result[1].price == 76.25

    def test_transform_data_unit_cleanup(self, mock_api_response_multiple):
        """Test that 'per ' prefix is removed from units."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
        )

        query = OilPriceAPIQueryParams()
        data = mock_api_response_multiple["data"]["prices"]
        result = OilPriceAPIFetcher.transform_data(query, data)

        assert result[0].unit == "barrel"  # Not "per barrel"

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        """Test that missing API key raises AuthenticationError."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            AuthenticationError,
        )

        query = OilPriceAPIQueryParams()
        with pytest.raises(AuthenticationError):
            await OilPriceAPIFetcher.aextract_data(query, None)

    @pytest.mark.asyncio
    async def test_empty_api_key_raises(self):
        """Test that empty API key raises AuthenticationError."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            AuthenticationError,
        )

        query = OilPriceAPIQueryParams()
        with pytest.raises(AuthenticationError):
            await OilPriceAPIFetcher.aextract_data(query, {"api_key": ""})

    @pytest.mark.asyncio
    async def test_auth_error_on_401(self, mock_api_response_multiple):
        """Test that 401 response raises AuthenticationError."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            AuthenticationError,
        )

        query = OilPriceAPIQueryParams()
        credentials = {"api_key": "invalid_key"}

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with pytest.raises(AuthenticationError):
                await OilPriceAPIFetcher.aextract_data(query, credentials)

    @pytest.mark.asyncio
    async def test_not_found_on_404(self):
        """Test that 404 response raises NotFoundError."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            NotFoundError,
        )

        query = OilPriceAPIQueryParams(symbol="WTI")
        credentials = {"api_key": "test_key"}

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with pytest.raises(NotFoundError):
                await OilPriceAPIFetcher.aextract_data(query, credentials)

    @pytest.mark.asyncio
    async def test_successful_fetch(self, mock_api_response_multiple):
        """Test successful data fetch."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
        )

        query = OilPriceAPIQueryParams()
        credentials = {"api_key": "test_key"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response_multiple

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await OilPriceAPIFetcher.aextract_data(query, credentials)

            assert len(result) == 2
            assert result[0]["code"] == "WTI_USD"

    @pytest.mark.asyncio
    async def test_successful_fetch_single_flat(self):
        """Test fetch with the current live API single-price shape.

        /v1/prices/latest returns the record directly under "data" with
        "price" as a number (not a nested object).
        """
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
        )

        flat_response = {
            "status": "success",
            "data": {
                "code": "WTI_USD",
                "price": 73.91,
                "currency": "USD",
                "unit": "barrel",
                "source": "market_reporting",
                "type": "spot_price",
                "created_at": "2026-07-13T13:11:44.152Z",
                "updated_at": "2026-07-13T13:11:44.152Z",
            },
        }

        query = OilPriceAPIQueryParams(symbol="WTI")
        credentials = {"api_key": "test_key"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = flat_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await OilPriceAPIFetcher.aextract_data(query, credentials)

        assert len(result) == 1
        assert result[0]["code"] == "WTI_USD"
        assert result[0]["price"] == 73.91

        transformed = OilPriceAPIFetcher.transform_data(query, result)
        assert transformed[0].symbol == "WTI"
        assert transformed[0].price == 73.91
        assert transformed[0].source == "market_reporting"

    def test_transform_rejects_missing_price(self):
        """A successful payload may not be normalized to a zero price."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            ResponseSchemaError,
        )

        with pytest.raises(ResponseSchemaError, match="price"):
            OilPriceAPIFetcher.transform_data(
                OilPriceAPIQueryParams(symbol="WTI"),
                [
                    {
                        "code": "WTI_USD",
                        "currency": "USD",
                        "unit": "barrel",
                        "updated_at": "2026-07-19T12:00:00Z",
                    }
                ],
            )

    @pytest.mark.parametrize("timestamp", [None, "not-a-timestamp"])
    def test_transform_rejects_missing_or_malformed_timestamp(self, timestamp):
        """The provider must not fabricate an observation timestamp."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            ResponseSchemaError,
        )

        item = {
            "code": "WTI_USD",
            "price": 73.91,
            "currency": "USD",
            "unit": "barrel",
        }
        if timestamp is not None:
            item["updated_at"] = timestamp

        with pytest.raises(ResponseSchemaError, match="timestamp"):
            OilPriceAPIFetcher.transform_data(
                OilPriceAPIQueryParams(symbol="WTI"), [item]
            )

    @pytest.mark.asyncio
    async def test_empty_success_response_raises_schema_error(self):
        """A 200 response without a price is not a successful provider result."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            ResponseSchemaError,
        )

        response = MagicMock(status_code=200)
        response.json.return_value = {"status": "success", "data": {}}
        with patch("httpx.AsyncClient") as mock_client:
            client = AsyncMock()
            client.get.return_value = response
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            mock_client.return_value = client

            with pytest.raises(ResponseSchemaError, match="usable price"):
                await OilPriceAPIFetcher.aextract_data(
                    OilPriceAPIQueryParams(symbol="WTI"), {"api_key": "test_key"}
                )

    @pytest.mark.asyncio
    async def test_entitlement_error_on_403(self):
        """Locked datasets return a typed error with a recovery URL."""
        from openbb_oilpriceapi.models.oil_price import (
            EntitlementError,
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
        )

        response = MagicMock(status_code=403)
        with patch("httpx.AsyncClient") as mock_client:
            client = AsyncMock()
            client.get.return_value = response
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            mock_client.return_value = client

            with pytest.raises(EntitlementError, match="oilpriceapi.com/pricing"):
                await OilPriceAPIFetcher.aextract_data(
                    OilPriceAPIQueryParams(symbol="WTI"), {"api_key": "test_key"}
                )

    @pytest.mark.asyncio
    async def test_timeout_is_mapped_to_provider_error(self):
        """Network timeouts expose an actionable typed error."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            ProviderTimeoutError,
        )

        with patch("httpx.AsyncClient") as mock_client:
            client = AsyncMock()
            client.get.side_effect = httpx.ReadTimeout("timed out")
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            mock_client.return_value = client

            with pytest.raises(ProviderTimeoutError, match="timed out"):
                await OilPriceAPIFetcher.aextract_data(
                    OilPriceAPIQueryParams(symbol="WTI"), {"api_key": "test_key"}
                )

    @pytest.mark.asyncio
    async def test_rate_limit_retries_three_times_then_raises(self):
        """A 429 is retried exactly three times without hiding exhaustion."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            RateLimitError,
        )

        response = MagicMock(status_code=429)
        client = AsyncMock()
        client.get.return_value = response
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        fast_retry = OilPriceAPIFetcher._fetch_with_retry.retry_with(wait=wait_none())

        with (
            patch("httpx.AsyncClient", return_value=client),
            patch.object(OilPriceAPIFetcher, "_fetch_with_retry", fast_retry),
            pytest.raises(RateLimitError, match="after 3 retries"),
        ):
            await OilPriceAPIFetcher.aextract_data(
                OilPriceAPIQueryParams(symbol="WTI"), {"api_key": "test_key"}
            )

        assert client.get.await_count == 3

    @pytest.mark.asyncio
    async def test_malformed_json_success_raises_schema_error(self):
        """A 200 with malformed JSON is a typed provider failure."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
            ResponseSchemaError,
        )

        response = MagicMock(status_code=200)
        response.json.side_effect = ValueError("invalid JSON")
        client = AsyncMock()
        client.get.return_value = response
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None

        with (
            patch("httpx.AsyncClient", return_value=client),
            pytest.raises(ResponseSchemaError, match="malformed JSON"),
        ):
            await OilPriceAPIFetcher.aextract_data(
                OilPriceAPIQueryParams(symbol="WTI"), {"api_key": "test_key"}
            )

    @pytest.mark.asyncio
    async def test_successful_fetch_single_legacy(self, mock_api_response_single):
        """Test fetch with the legacy nested single-price shape."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
        )

        query = OilPriceAPIQueryParams(symbol="WTI")
        credentials = {"api_key": "test_key"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response_single

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await OilPriceAPIFetcher.aextract_data(query, credentials)

        assert len(result) == 1
        assert result[0]["code"] == "WTI_USD"
        assert result[0]["price"] == 72.50


class TestSymbolMapping:
    """Test cases for commodity symbol mapping."""

    def test_openbb_to_oilpriceapi_mapping(self):
        """Test mapping from OpenBB symbols to OilPriceAPI codes."""
        from openbb_oilpriceapi.utils.constants import SYMBOL_MAPPING

        assert SYMBOL_MAPPING["WTI"] == "WTI_USD"
        assert SYMBOL_MAPPING["BRENT"] == "BRENT_CRUDE_USD"
        assert SYMBOL_MAPPING["URALS"] == "URALS_CRUDE_USD"
        assert SYMBOL_MAPPING["NG"] == "NATURAL_GAS_USD"

    def test_reverse_mapping(self):
        """Test reverse mapping from OilPriceAPI codes to OpenBB symbols."""
        from openbb_oilpriceapi.utils.constants import REVERSE_SYMBOL_MAPPING

        assert REVERSE_SYMBOL_MAPPING["WTI_USD"] == "WTI"
        assert REVERSE_SYMBOL_MAPPING["BRENT_CRUDE_USD"] == "BRENT"
        assert REVERSE_SYMBOL_MAPPING["URALS_CRUDE_USD"] == "URALS"

    def test_available_symbols(self):
        """Test list of available symbols."""
        from openbb_oilpriceapi.utils.constants import AVAILABLE_SYMBOLS

        assert "WTI" in AVAILABLE_SYMBOLS
        assert "BRENT" in AVAILABLE_SYMBOLS
        assert "URALS" in AVAILABLE_SYMBOLS
        assert "NG" in AVAILABLE_SYMBOLS
        assert "COAL" in AVAILABLE_SYMBOLS
        assert len(AVAILABLE_SYMBOLS) == 10


class TestProviderRegistration:
    """Test cases for provider registration."""

    def test_provider_exists(self):
        """Test that provider is properly defined."""
        from openbb_oilpriceapi import oilpriceapi_provider

        assert oilpriceapi_provider.name == "oilpriceapi"
        assert "oilpriceapi_api_key" in oilpriceapi_provider.credentials

    def test_provider_has_fetchers(self):
        """Test that provider has required fetchers registered."""
        from openbb_oilpriceapi import oilpriceapi_provider

        assert "OilPrice" in oilpriceapi_provider.fetcher_dict

    def test_provider_website(self):
        """Test provider website is set."""
        from openbb_oilpriceapi import oilpriceapi_provider

        assert oilpriceapi_provider.website == "https://www.oilpriceapi.com"

    def test_provider_description(self):
        """Test provider has description."""
        from openbb_oilpriceapi import oilpriceapi_provider

        assert "oil" in oilpriceapi_provider.description.lower()
        assert "commodity" in oilpriceapi_provider.description.lower()


class TestErrorClasses:
    """Test custom error classes."""

    def test_authentication_error(self):
        """Test AuthenticationError is properly defined."""
        from openbb_oilpriceapi.models.oil_price import (
            AuthenticationError,
            OilPriceAPIError,
        )

        error = AuthenticationError("Invalid API key")
        assert isinstance(error, OilPriceAPIError)
        assert str(error) == "Invalid API key"

    def test_rate_limit_error(self):
        """Test RateLimitError is properly defined."""
        from openbb_oilpriceapi.models.oil_price import (
            RateLimitError,
            OilPriceAPIError,
        )

        error = RateLimitError("Rate limit exceeded")
        assert isinstance(error, OilPriceAPIError)

    def test_not_found_error(self):
        """Test NotFoundError is properly defined."""
        from openbb_oilpriceapi.models.oil_price import NotFoundError, OilPriceAPIError

        error = NotFoundError("Commodity not found")
        assert isinstance(error, OilPriceAPIError)
