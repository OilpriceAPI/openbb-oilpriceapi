# Reddit Posts

## r/algotrading

### Title
Open-sourced an OpenBB provider for real-time oil & commodity prices

### Body
I've been working on a trading system that needs commodity prices, and found it frustrating that OpenBB didn't have a dedicated provider for oil data. So I built one.

**What it does:**
- Real-time prices for WTI, Brent, Urals, Dubai crude
- Natural gas (Henry Hub, TTF, NBP)
- Coal, diesel, gasoline
- Historical data (hourly/daily)

**Install:**
```bash
pip install openbb-oilpriceapi
```

**Example:**
```python
from openbb import obb

obb.user.credentials.oilpriceapi_api_key = "your_key"

# Get all prices
prices = obb.commodity.oil.price(provider="oilpriceapi")
df = prices.to_dataframe()

# Get historical WTI for backtesting
history = obb.commodity.oil.historical(symbol="WTI", period="past_month", provider="oilpriceapi")
```

Free tier has 100 req/month which is enough for daily analysis. Paid tiers go up from there.

Links:
- PyPI: https://pypi.org/project/openbb-oilpriceapi/
- GitHub: https://github.com/OilpriceAPI/openbb-oilpriceapi
- Get API key: https://oilpriceapi.com

Would love feedback from anyone working with commodity data!

---

## r/Python

### Title
Built an OpenBB extension for commodity prices - my first PyPI package

### Body
Just published my first proper Python package to PyPI! It's an OpenBB provider extension for fetching oil and commodity prices.

**The stack:**
- Poetry for packaging
- Pydantic for data models
- httpx for async HTTP
- tenacity for retry logic
- pytest with 89% coverage
- GitHub Actions CI/CD

**What I learned:**
1. OpenBB's provider architecture is really well designed - Fetcher pattern with transform_query, aextract_data, transform_data
2. PyPI publishing with Poetry is straightforward once you figure out the token scoping
3. Tenacity makes retry logic trivial

**Install:**
```bash
pip install openbb-oilpriceapi
```

Code is MIT licensed: https://github.com/OilpriceAPI/openbb-oilpriceapi

Happy to answer questions about the implementation or OpenBB provider development!
