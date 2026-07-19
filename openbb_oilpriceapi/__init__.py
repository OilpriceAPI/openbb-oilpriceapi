"""OpenBB provider fetchers for versioned OilPriceAPI price endpoints."""

from openbb_core.provider.abstract.provider import Provider
from openbb_oilpriceapi.models.oil_price import OilPriceAPIFetcher
from openbb_oilpriceapi.models.oil_historical import OilHistoricalFetcher

oilpriceapi_provider = Provider(
    name="oilpriceapi",
    website="https://www.oilpriceapi.com",
    description=(
        "Source-timestamped energy and commodity price records from versioned OilPriceAPI "
        "endpoints. Dataset access depends on the API key's entitlements."
    ),
    credentials=["api_key"],
    fetcher_dict={
        "OilPrice": OilPriceAPIFetcher,
        "OilHistorical": OilHistoricalFetcher,
    },
    repr_name="OilPriceAPI",
    instructions=(
        "Create or manage a key at https://www.oilpriceapi.com/auth/signup\n"
        "Credential name: oilpriceapi_api_key"
    ),
)

__all__ = ["oilpriceapi_provider"]
