# openbb-oilpriceapi

[![PyPI version](https://badge.fury.io/py/openbb-oilpriceapi.svg)](https://badge.fury.io/py/openbb-oilpriceapi)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

OpenBB provider for [OilPriceAPI](https://oilpriceapi.com) - Real-time oil and commodity prices.

## Installation

```bash
pip install openbb-oilpriceapi
```

## Quick Start

```python
from openbb import obb

# Configure your API key (get free key at https://oilpriceapi.com/signup)
obb.user.credentials.oilpriceapi_api_key = "your_api_key"

# Get all commodity prices
prices = obb.commodity.oil.price(provider="oilpriceapi")
df = prices.to_dataframe()
print(df)

# Get specific commodity (WTI crude)
wti = obb.commodity.oil.price(symbol="WTI", provider="oilpriceapi")
print(f"WTI Price: ${wti.results[0].price}/barrel")
```

## Supported Commodities

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

## Configuration

### Set Credentials

You can set your API key in multiple ways:

**Option 1: In Python**
```python
obb.user.credentials.oilpriceapi_api_key = "your_key"
```

**Option 2: Via settings file**
Add to `~/.openbb_platform/user_settings.json`:
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

## Examples

### Get Price History

```python
# Get WTI prices for the past week
history = obb.commodity.oil.historical(
    symbol="WTI",
    period="past_week",
    provider="oilpriceapi"
)
df = history.to_dataframe()
```

### Compare Commodities

```python
import pandas as pd

# Get all prices and compare
prices = obb.commodity.oil.price(provider="oilpriceapi")
df = prices.to_dataframe()

# Filter for crude oils
crude = df[df['symbol'].isin(['WTI', 'BRENT', 'URALS'])]
print(crude[['symbol', 'price', 'change_percent']])
```

### Visualize Prices

```python
import matplotlib.pyplot as plt

history = obb.commodity.oil.historical(
    symbol="BRENT",
    period="past_month",
    provider="oilpriceapi"
)
df = history.to_dataframe()

plt.figure(figsize=(10, 6))
plt.plot(df['date'], df['price'])
plt.title('Brent Crude - Past Month')
plt.ylabel('Price (USD/barrel)')
plt.show()
```

## API Reference

### OilPrice

Fetch latest commodity prices.

**Parameters:**
- `symbol` (str, optional): Commodity symbol. If not provided, returns all commodities.
- `provider` (str): Must be "oilpriceapi"

**Returns:**
- `symbol`: Commodity symbol
- `name`: Commodity name
- `price`: Current price
- `currency`: Price currency
- `unit`: Unit of measurement
- `updated_at`: Last update timestamp
- `change`: Price change (absolute)
- `change_percent`: Price change (percentage)

### OilHistorical

Fetch historical price data.

**Parameters:**
- `symbol` (str, required): Commodity symbol
- `period` (str): Historical period - `past_day` (24h hourly), `past_week` (7d daily), `past_month` (30d daily). Default: `past_week`
- `provider` (str): Must be "oilpriceapi"

**Returns:**
- `date`: Price timestamp
- `symbol`: Commodity symbol
- `price`: Price at timestamp
- `currency`: Price currency
- `unit`: Unit of measurement

## Development

```bash
# Clone the repository
git clone https://github.com/OilpriceAPI/openbb-oilpriceapi.git
cd openbb-oilpriceapi

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=openbb_oilpriceapi
```

## Links

- [OilPriceAPI Website](https://oilpriceapi.com)
- [OilPriceAPI Documentation](https://docs.oilpriceapi.com)
- [OpenBB Platform](https://openbb.co)
- [GitHub Repository](https://github.com/OilpriceAPI/openbb-oilpriceapi)

## License

MIT License - see [LICENSE](LICENSE) for details.
