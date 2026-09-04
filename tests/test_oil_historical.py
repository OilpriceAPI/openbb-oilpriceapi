"""Tests for OilPriceAPI historical price fetcher."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestOilHistoricalQueryParams:
    """Test cases for OilHistoricalQueryParams data model."""

    def test_default_period(self):
        """Test default period is past_week."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalQueryParams

        params = OilHistoricalQueryParams(symbol="WTI")
        assert params.period == "past_week"

    def test_symbol_required(self):
        """Test that symbol is required."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalQueryParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OilHistoricalQueryParams()

    def test_valid_periods(self):
        """Test all valid periods."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalQueryParams

        for period in ["past_day", "past_week", "past_month", "past_year"]:
            params = OilHistoricalQueryParams(symbol="WTI", period=period)
            assert params.period == period

    def test_invalid_period_raises(self):
        """Test that invalid period raises validation error."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalQueryParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OilHistoricalQueryParams(symbol="WTI", period="past_decade")

    def test_symbol_case_insensitive(self):
        """Test that symbol is case-insensitive."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalQueryParams

        params = OilHistoricalQueryParams(symbol="wti")
        assert params.symbol == "WTI"

    def test_invalid_symbol_raises(self):
        """Test that invalid symbol raises validation error."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalQueryParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OilHistoricalQueryParams(symbol="INVALID")


class TestOilHistoricalData:
    """Test cases for OilHistoricalData data model."""

    def test_data_model_fields(self):
        """Test that data model has required fields."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalData

        data = OilHistoricalData(
            date=datetime.now(),
            symbol="WTI",
            price=72.50,
            currency="USD",
            unit="barrel",
        )
        assert data.symbol == "WTI"
        assert data.price == 72.50
        assert data.currency == "USD"
        assert data.unit == "barrel"

    def test_currency_and_unit_are_required(self):
        """Historical results must not fabricate currency or unit."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalData
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OilHistoricalData(
                date=datetime.now(),
                symbol="WTI",
                price=72.50,
            )


class TestOilHistoricalFetcher:
    """Test cases for OilHistoricalFetcher."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response with historical prices."""
        return {
            "data": {
                "prices": [
                    {
                        "code": "WTI_USD",
                        "price": 70.00,
                        "currency": "USD",
                        "unit": "per barrel",
                        "created_at": "2025-12-20T12:00:00Z",
                        "source": "market_reporting",
                    },
                    {
                        "code": "WTI_USD",
                        "price": 71.00,
                        "currency": "USD",
                        "unit": "per barrel",
                        "created_at": "2025-12-21T12:00:00Z",
                    },
                    {
                        "code": "WTI_USD",
                        "price": 72.50,
                        "currency": "USD",
                        "unit": "per barrel",
                        "created_at": "2025-12-22T12:00:00Z",
                    },
                ]
            }
        }

    def test_transform_query(self):
        """Test query transformation."""
        from openbb_oilpriceapi.models.oil_historical import OilHistoricalFetcher

        params = {"symbol": "WTI", "period": "past_week"}
        query = OilHistoricalFetcher.transform_query(params)
        assert query.symbol == "WTI"
        assert query.period == "past_week"

    def test_transform_data(self, mock_api_response):
        """Test data transformation."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
            OilHistoricalData,
        )

        query = OilHistoricalQueryParams(symbol="WTI")
        data = mock_api_response["data"]["prices"]
        result = OilHistoricalFetcher.transform_data(query, data)

        assert len(result) == 3
        assert isinstance(result[0], OilHistoricalData)
        assert result[0].symbol == "WTI"
        # Should be sorted by date ascending
        assert result[0].price == 70.00
        assert result[1].price == 71.00
        assert result[2].price == 72.50

    def test_transform_data_sorted_by_date(self, mock_api_response):
        """Test that results are sorted by date ascending."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
        )

        query = OilHistoricalQueryParams(symbol="WTI")
        # Reverse the order to test sorting
        data = list(reversed(mock_api_response["data"]["prices"]))
        result = OilHistoricalFetcher.transform_data(query, data)

        # Should still be sorted ascending
        assert result[0].date < result[1].date < result[2].date

    def test_transform_data_unit_cleanup(self, mock_api_response):
        """Test that 'per ' prefix is removed from units."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
        )

        query = OilHistoricalQueryParams(symbol="WTI")
        data = mock_api_response["data"]["prices"]
        result = OilHistoricalFetcher.transform_data(query, data)

        assert result[0].unit == "barrel"  # Not "per barrel"
        assert result[0].source == "market_reporting"

    def test_transform_rejects_missing_or_malformed_fields(self):
        """Historical transformation rejects schema drift instead of skipping it."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
        )
        from openbb_oilpriceapi.models.oil_price import ResponseSchemaError

        query = OilHistoricalQueryParams(symbol="WTI")
        for item in [
            {
                "code": "WTI_USD",
                "currency": "USD",
                "unit": "barrel",
                "created_at": "2026-07-19T12:00:00Z",
            },
            {"code": "WTI_USD", "price": 70.0, "currency": "USD", "unit": "barrel"},
            {
                "code": "WTI_USD",
                "price": 70.0,
                "currency": "USD",
                "unit": "barrel",
                "created_at": "not-a-date",
            },
        ]:
            with pytest.raises(ResponseSchemaError):
                OilHistoricalFetcher.transform_data(query, [item])

    @pytest.mark.asyncio
    async def test_empty_success_response_raises_schema_error(self):
        """A historical 200 without records is not a successful result."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
        )
        from openbb_oilpriceapi.models.oil_price import ResponseSchemaError

        response = MagicMock(status_code=200)
        response.json.return_value = {"status": "success", "data": {"prices": []}}
        with patch("httpx.AsyncClient") as mock_client:
            client = AsyncMock()
            client.get.return_value = response
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            mock_client.return_value = client

            with pytest.raises(ResponseSchemaError, match="historical"):
                await OilHistoricalFetcher.aextract_data(
                    OilHistoricalQueryParams(symbol="WTI"), {"api_key": "test_key"}
                )

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        """Test that missing API key raises AuthenticationError."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
        )
        from openbb_oilpriceapi.models.oil_price import AuthenticationError

        query = OilHistoricalQueryParams(symbol="WTI")
        with pytest.raises(AuthenticationError):
            await OilHistoricalFetcher.aextract_data(query, None)

    @pytest.mark.asyncio
    async def test_successful_fetch(self, mock_api_response):
        """Test successful data fetch."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
        )

        query = OilHistoricalQueryParams(symbol="WTI", period="past_week")
        credentials = {"api_key": "test_key"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await OilHistoricalFetcher.aextract_data(query, credentials)

            assert len(result) == 3
            # Verify URL contains correct period
            call_args = mock_instance.get.call_args
            assert "past_week" in call_args[0][0]
            assert "WTI_USD" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_past_year_fetch_uses_versioned_endpoint(self, mock_api_response):
        """The added period must reach the API instead of only validating locally."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
        )

        response = MagicMock(status_code=200)
        response.json.return_value = mock_api_response

        with patch("httpx.AsyncClient") as mock_client:
            client = AsyncMock()
            client.get.return_value = response
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            mock_client.return_value = client

            await OilHistoricalFetcher.aextract_data(
                OilHistoricalQueryParams(symbol="WTI", period="past_year"),
                {"api_key": "test_key"},
            )

        assert "/prices/past_year?" in client.get.call_args.args[0]

    @pytest.mark.asyncio
    async def test_auth_error_on_401(self):
        """Test that 401 response raises AuthenticationError."""
        from openbb_oilpriceapi.models.oil_historical import (
            OilHistoricalFetcher,
            OilHistoricalQueryParams,
        )
        from openbb_oilpriceapi.models.oil_price import AuthenticationError

        query = OilHistoricalQueryParams(symbol="WTI")
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
                await OilHistoricalFetcher.aextract_data(query, credentials)


class TestHistoricalProviderRegistration:
    """Test cases for historical fetcher provider registration."""

    def test_historical_fetcher_registered(self):
        """Test that historical fetcher is registered with provider."""
        from openbb_oilpriceapi import oilpriceapi_provider

        assert "OilHistorical" in oilpriceapi_provider.fetcher_dict

    def test_fetcher_count(self):
        """Test that provider has both fetchers."""
        from openbb_oilpriceapi import oilpriceapi_provider

        assert len(oilpriceapi_provider.fetcher_dict) == 2
        assert "OilPrice" in oilpriceapi_provider.fetcher_dict
        assert "OilHistorical" in oilpriceapi_provider.fetcher_dict
