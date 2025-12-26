# OpenBB Discord Announcement

## Channel
#extensions or #showcase

## Message

Hey everyone! 👋

Just published a new provider extension: **openbb-oilpriceapi**

It adds real-time oil and commodity prices to OpenBB:

**Commodities supported:**
- Crude oils: WTI, Brent, Urals, Dubai
- Natural gas: US (Henry Hub), EU (TTF), UK (NBP)
- Others: Coal, Diesel, Gasoline

**Install:**
```
pip install openbb-oilpriceapi
```

**Usage:**
```python
from openbb import obb
obb.user.credentials.oilpriceapi_api_key = "your_key"

# Latest prices
prices = obb.commodity.oil.price(provider="oilpriceapi")

# Historical data
history = obb.commodity.oil.historical(symbol="WTI", period="past_week", provider="oilpriceapi")
```

**Features:**
- Two fetchers: OilPrice (latest) and OilHistorical (past_day/week/month)
- Built-in retry logic for rate limits
- 89% test coverage
- MIT licensed

**Links:**
- PyPI: <https://pypi.org/project/openbb-oilpriceapi/>
- GitHub: <https://github.com/OilpriceAPI/openbb-oilpriceapi>
- Free API key: <https://oilpriceapi.com/signup>

Also opened an issue (#7291) about potentially including it as a core provider. Would love any feedback! 🙏
