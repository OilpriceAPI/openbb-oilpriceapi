---
title: Access Real-Time Oil Prices in Python with OpenBB and OilPriceAPI
published: true
description: Learn how to fetch and analyze oil and commodity prices using OpenBB Platform with the OilPriceAPI provider extension.
tags: python, finance, api, datascience
cover_image: https://oilpriceapi.com/og-image.png
---

# Access Real-Time Oil Prices in Python with OpenBB and OilPriceAPI

If you're building trading algorithms, financial dashboards, or data analysis pipelines that need commodity prices, you know the pain of finding reliable, affordable data sources. Today I'm sharing a new OpenBB provider that gives you access to real-time oil and commodity prices with just a few lines of Python.

## What We're Building

By the end of this tutorial, you'll be able to:
- Fetch real-time prices for WTI, Brent, and other crude oils
- Get natural gas, coal, diesel, and gasoline prices
- Retrieve historical price data for analysis
- Create visualizations of commodity price trends

## Prerequisites

- Python 3.10+
- Free OilPriceAPI key (get one at [oilpriceapi.com](https://oilpriceapi.com/signup))

## Installation

```bash
pip install openbb openbb-oilpriceapi
```

## Quick Start

```python
from openbb import obb

# Configure your API key
obb.user.credentials.oilpriceapi_api_key = "your_api_key_here"

# Get all commodity prices
prices = obb.commodity.oil.price(provider="oilpriceapi")
df = prices.to_dataframe()
print(df)
```

Output:
```
   symbol              name   price currency     unit  change  change_percent
0     WTI    WTI Crude Oil   69.77      USD   barrel   -0.31           -0.44
1   BRENT  Brent Crude Oil   73.20      USD   barrel   -0.42           -0.57
2   URALS  Urals Crude Oil   62.88      USD   barrel    0.15            0.24
3      NG      Natural Gas    3.49      USD    therm    0.05            1.45
...
```

## Available Commodities

The provider supports 10 commodities across four categories:

| Symbol | Name | Description |
|--------|------|-------------|
| `WTI` | WTI Crude Oil | West Texas Intermediate benchmark |
| `BRENT` | Brent Crude Oil | North Sea benchmark |
| `URALS` | Urals Crude Oil | Russian export blend |
| `DUBAI` | Dubai Crude Oil | Middle East benchmark |
| `NG` | Natural Gas (US) | Henry Hub |
| `NG_EU` | Natural Gas (EU) | TTF |
| `NG_UK` | Natural Gas (UK) | NBP |
| `COAL` | Coal | Thermal coal |
| `DIESEL_US` | US Diesel | National average |
| `GASOLINE_US` | US Gasoline | National average |

## Fetching Specific Commodities

```python
# Get just WTI crude
wti = obb.commodity.oil.price(symbol="WTI", provider="oilpriceapi")
print(f"WTI: ${wti.results[0].price}/barrel ({wti.results[0].change_percent:+.2f}%)")

# Get natural gas
ng = obb.commodity.oil.price(symbol="NG", provider="oilpriceapi")
print(f"Natural Gas: ${ng.results[0].price}/therm")
```

## Historical Data

Need to analyze price trends? The provider includes historical data:

```python
# Get WTI prices for the past week
history = obb.commodity.oil.historical(
    symbol="WTI",
    period="past_week",  # Options: past_day, past_week, past_month
    provider="oilpriceapi"
)

df = history.to_dataframe()
print(df.head())
```

Available periods:
- `past_day` - Hourly prices for 24 hours
- `past_week` - Daily prices for 7 days
- `past_month` - Daily prices for 30 days

## Practical Example: Price Comparison Dashboard

Let's build a simple price comparison:

```python
import pandas as pd
from openbb import obb

obb.user.credentials.oilpriceapi_api_key = "your_key"

# Get all prices
prices = obb.commodity.oil.price(provider="oilpriceapi")
df = prices.to_dataframe()

# Filter crude oils only
crude_oils = df[df['symbol'].isin(['WTI', 'BRENT', 'URALS', 'DUBAI'])]

# Calculate spread
brent_wti_spread = crude_oils[crude_oils['symbol'] == 'BRENT']['price'].values[0] - \
                   crude_oils[crude_oils['symbol'] == 'WTI']['price'].values[0]

print("=== Crude Oil Prices ===")
for _, row in crude_oils.iterrows():
    print(f"{row['symbol']:8} ${row['price']:6.2f}  ({row['change_percent']:+.2f}%)")

print(f"\nBrent-WTI Spread: ${brent_wti_spread:.2f}")
```

## Visualizing Price History

```python
import matplotlib.pyplot as plt

# Get monthly history for Brent
history = obb.commodity.oil.historical(
    symbol="BRENT",
    period="past_month",
    provider="oilpriceapi"
)
df = history.to_dataframe()

# Plot
plt.figure(figsize=(12, 6))
plt.plot(df['date'], df['price'], marker='o', linewidth=2)
plt.title('Brent Crude Oil - Past Month', fontsize=14)
plt.xlabel('Date')
plt.ylabel('Price (USD/barrel)')
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

## Error Handling

The provider includes built-in retry logic for rate limits:

```python
from openbb_oilpriceapi.models import AuthenticationError, RateLimitError, NotFoundError

try:
    prices = obb.commodity.oil.price(provider="oilpriceapi")
except AuthenticationError:
    print("Invalid API key - check your credentials")
except RateLimitError:
    print("Rate limit hit - the provider will auto-retry 3 times")
except NotFoundError:
    print("Commodity not found")
```

## Configuration Options

### Setting Credentials

**Option 1: In Python**
```python
obb.user.credentials.oilpriceapi_api_key = "your_key"
```

**Option 2: Settings file** (`~/.openbb_platform/user_settings.json`)
```json
{
  "credentials": {
    "oilpriceapi_api_key": "your_key"
  }
}
```

**Option 3: Environment variable**
```bash
export OPENBB_OILPRICEAPI_API_KEY="your_key"
```

## Why OpenBB + OilPriceAPI?

1. **Unified Interface** - Same API pattern as other OpenBB providers
2. **DataFrame Ready** - Convert to pandas with `.to_dataframe()`
3. **Reliable** - Built-in retry logic handles rate limits gracefully
4. **Free Tier** - Get started with 100 requests/month free
5. **Real-Time** - Prices updated throughout the trading day

## Links

- [openbb-oilpriceapi on PyPI](https://pypi.org/project/openbb-oilpriceapi/)
- [GitHub Repository](https://github.com/OilpriceAPI/openbb-oilpriceapi)
- [OilPriceAPI Documentation](https://docs.oilpriceapi.com)
- [Get Free API Key](https://oilpriceapi.com/signup)
- [OpenBB Platform](https://openbb.co)

---

*Have questions or feedback? Open an issue on [GitHub](https://github.com/OilpriceAPI/openbb-oilpriceapi/issues) or reach out on [Twitter](https://twitter.com/oilpriceapi).*
