# Hacker News Show HN Post

## Title
Show HN: OpenBB provider for real-time oil and commodity prices

## URL
https://github.com/OilpriceAPI/openbb-oilpriceapi

## Text (for self-post if needed)
Hey HN,

I built an OpenBB provider extension that adds real-time oil and commodity prices to the OpenBB Platform.

**What it does:**
- Fetches prices for WTI, Brent, Urals crude oil, natural gas (US/EU/UK), coal, diesel, and gasoline
- Historical data (hourly/daily) for analysis
- Built-in retry logic with exponential backoff
- 89% test coverage

**Install:**
```
pip install openbb-oilpriceapi
```

**Usage:**
```python
from openbb import obb
obb.user.credentials.oilpriceapi_api_key = "your_key"
prices = obb.commodity.oil.price(provider="oilpriceapi")
```

Free tier includes 100 requests/month. Built this because I needed reliable commodity data for a trading project and wanted it to work seamlessly with OpenBB's excellent data platform.

GitHub: https://github.com/OilpriceAPI/openbb-oilpriceapi
PyPI: https://pypi.org/project/openbb-oilpriceapi/
