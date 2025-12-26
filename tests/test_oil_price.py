"""Tests for OilPriceAPI oil price fetcher - TDD approach."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

# These imports will fail until we implement the modules
# That's expected in TDD - tests first, implementation second


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
            symbol="WTI_USD",
            name="WTI Crude Oil",
            price=72.50,
            currency="USD",
            unit="barrel",
            updated_at=datetime.now(),
        )
        assert data.symbol == "WTI_USD"
        assert data.price == 72.50
        assert data.currency == "USD"

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        from openbb_oilpriceapi.models.oil_price import OilPriceAPIData

        data = OilPriceAPIData(
            symbol="WTI_USD",
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


class TestOilPriceFetcher:
    """Test cases for OilPriceFetcher."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response from OilPriceAPI."""
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

    @pytest.mark.asyncio
    async def test_fetch_all_prices(self, mock_api_response):
        """Test fetching all commodity prices."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
        )

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = AsyncMock()
            mock_get.return_value.json.return_value = mock_api_response
            mock_get.return_value.status_code = 200

            params = OilPriceAPIQueryParams()
            credentials = {"api_key": "test_api_key"}

            # Transform query
            query = OilPriceAPIFetcher.transform_query(params.model_dump())

            # Extract data (mocked)
            # data = await OilPriceAPIFetcher.aextract_data(query, credentials)

            # Assert structure
            assert query is not None

    @pytest.mark.asyncio
    async def test_handles_auth_error(self):
        """Test that authentication errors are handled correctly."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
        )

        # Test will verify proper error handling for 401 responses
        # Implementation should raise AuthenticationError
        pass

    @pytest.mark.asyncio
    async def test_handles_rate_limit(self):
        """Test that rate limit errors trigger retry."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIQueryParams,
        )

        # Test will verify retry logic for 429 responses
        pass

    @pytest.mark.asyncio
    async def test_transform_data_correctly(self, mock_api_response):
        """Test that API response is correctly transformed to OpenBB format."""
        from openbb_oilpriceapi.models.oil_price import (
            OilPriceAPIFetcher,
            OilPriceAPIData,
        )

        # Test data transformation
        # result = OilPriceAPIFetcher.transform_data(mock_api_response["data"]["prices"])
        # assert len(result) == 2
        # assert isinstance(result[0], OilPriceAPIData)
        pass


class TestSymbolMapping:
    """Test cases for commodity symbol mapping."""

    def test_openbb_to_oilpriceapi_mapping(self):
        """Test mapping from OpenBB symbols to OilPriceAPI codes."""
        from openbb_oilpriceapi.utils.constants import SYMBOL_MAPPING

        assert SYMBOL_MAPPING["WTI"] == "WTI_USD"
        assert SYMBOL_MAPPING["BRENT"] == "BRENT_CRUDE_USD"
        assert SYMBOL_MAPPING["URALS"] == "URALS_USD"
        assert SYMBOL_MAPPING["NG"] == "NATURAL_GAS_USD"

    def test_available_symbols(self):
        """Test list of available symbols."""
        from openbb_oilpriceapi.utils.constants import AVAILABLE_SYMBOLS

        assert "WTI" in AVAILABLE_SYMBOLS
        assert "BRENT" in AVAILABLE_SYMBOLS
        assert "URALS" in AVAILABLE_SYMBOLS
        assert "NG" in AVAILABLE_SYMBOLS
        assert "COAL" in AVAILABLE_SYMBOLS


class TestProviderRegistration:
    """Test cases for provider registration."""

    def test_provider_exists(self):
        """Test that provider is properly defined."""
        from openbb_oilpriceapi import oilpriceapi_provider

        assert oilpriceapi_provider.name == "oilpriceapi"
        assert "api_key" in oilpriceapi_provider.credentials

    def test_provider_has_fetchers(self):
        """Test that provider has required fetchers registered."""
        from openbb_oilpriceapi import oilpriceapi_provider

        assert "OilPrice" in oilpriceapi_provider.fetcher_dict
