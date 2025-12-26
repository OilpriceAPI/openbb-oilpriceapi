"""OpenBB OilPriceAPI Provider Module.

This provider enables access to real-time oil and commodity prices
from OilPriceAPI through the OpenBB Platform.

Supported commodities:
- WTI Crude Oil (WTI)
- Brent Crude Oil (BRENT)
- Urals Crude Oil (URALS)
- Dubai Crude Oil (DUBAI)
- Natural Gas US (NG)
- Natural Gas EU (NG_EU)
- Natural Gas UK (NG_UK)
- Coal (COAL)
- Diesel US (DIESEL_US)
- Gasoline US (GASOLINE_US)

Usage:
    from openbb import obb

    # Configure credentials
    obb.user.credentials.oilpriceapi_api_key = "your_api_key"

    # Get all prices
    prices = obb.commodity.oil.price(provider="oilpriceapi")

    # Get specific commodity
    wti = obb.commodity.oil.price(symbol="WTI", provider="oilpriceapi")
"""

from openbb_core.provider.abstract.provider import Provider
from openbb_oilpriceapi.models.oil_price import OilPriceAPIFetcher
from openbb_oilpriceapi.models.oil_historical import OilHistoricalFetcher

oilpriceapi_provider = Provider(
    name="oilpriceapi",
    website="https://oilpriceapi.com",
    description=(
        "OilPriceAPI provides real-time and historical oil and commodity prices "
        "including WTI, Brent, Urals crude oil, natural gas, coal, and diesel. "
        "Get your free API key at https://oilpriceapi.com"
    ),
    credentials=["api_key"],
    fetcher_dict={
        "OilPrice": OilPriceAPIFetcher,
        "OilHistorical": OilHistoricalFetcher,
    },
    repr_name="OilPriceAPI",
    instructions=(
        "Get your free API key at https://oilpriceapi.com/signup\n"
        "Set credentials: obb.user.credentials.oilpriceapi_api_key = 'your_key'"
    ),
)

__all__ = ["oilpriceapi_provider"]
