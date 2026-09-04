# openbb-oilpriceapi

[![PyPI version](https://badge.fury.io/py/openbb-oilpriceapi.svg)](https://pypi.org/project/openbb-oilpriceapi/)
[![CI](https://github.com/OilpriceAPI/openbb-oilpriceapi/actions/workflows/ci.yml/badge.svg)](https://github.com/OilpriceAPI/openbb-oilpriceapi/actions/workflows/ci.yml)

OpenBB provider fetchers for source-timestamped records from
[OilPriceAPI](https://www.oilpriceapi.com). Dataset access depends on the API
key's plan, source, and account entitlements.

## Install

```bash
python -m pip install openbb-oilpriceapi
```

The package registers the `oilpriceapi` provider extension and these provider
models:

| Provider model | Fetcher | Purpose |
| --- | --- | --- |
| `OilPrice` | `OilPriceAPIFetcher` | Latest available price record |
| `OilHistorical` | `OilHistoricalFetcher` | Versioned historical-period records |

These are provider fetchers, not an OpenBB router extension. OpenBB documents
direct fetcher execution as the supported way to use a provider independently
of a router.

## Quickstart

Create or manage a key at the
[OilPriceAPI signup page](https://www.oilpriceapi.com/auth/signup?utm_source=openbb&utm_medium=integration&utm_campaign=readme),
then set it outside your source code:

```bash
export OPENBB_OILPRICEAPI_API_KEY="your_key"
python examples/quickstart.py BRENT
```

The equivalent Python query is:

```python
import asyncio
import os

from openbb_oilpriceapi.models import OilPriceAPIFetcher

prices = asyncio.run(
    OilPriceAPIFetcher.fetch_data(
        {"symbol": "BRENT"},
        {"api_key": os.environ["OPENBB_OILPRICEAPI_API_KEY"]},
    )
)
record = prices[0]
print(record.symbol, record.price, record.currency, record.updated_at, record.source)
```

For an OpenBB application settings file, the credential name is
`oilpriceapi_api_key`. After installing a provider into an existing OpenBB
environment, rebuild its extension map as described in the
[OpenBB provider documentation](https://docs.openbb.co/odp/python/extensions/providers).

## Symbols

The package deliberately exposes a curated, versioned set of OpenBB-style
symbols rather than dynamically importing `/commodities`. OpenBB query choices
must be deterministic, while the API catalog and account entitlements can
change independently. A mapping means the provider can construct the request;
it does not guarantee that every API key can access that dataset. New mappings
are reviewed and shipped in provider releases.

| Symbol | OilPriceAPI code |
| --- | --- |
| `WTI` | `WTI_USD` |
| `BRENT` | `BRENT_CRUDE_USD` |
| `URALS` | `URALS_CRUDE_USD` |
| `DUBAI` | `DUBAI_CRUDE_USD` |
| `NG` | `NATURAL_GAS_USD` |
| `NG_EU` | `DUTCH_TTF_EUR` |
| `NG_UK` | `NATURAL_GAS_GBP` |
| `COAL` | `COAL_USD` |
| `DIESEL_US` | `DIESEL_USD` |
| `GASOLINE_US` | `GASOLINE_USD` |

Omitting `symbol` from `OilPriceAPIFetcher` requests the API's default latest
record. It does not request the complete catalog.

## Historical Query

```python
import asyncio
import os

from openbb_oilpriceapi.models import OilHistoricalFetcher

history = asyncio.run(
    OilHistoricalFetcher.fetch_data(
        {"symbol": "WTI", "period": "past_week"},
        {"api_key": os.environ["OPENBB_OILPRICEAPI_API_KEY"]},
    )
)
for record in history:
    print(record.date, record.price, record.currency, record.unit, record.source)
```

Supported request values are `past_day`, `past_week`, `past_month`, and
`past_year`.
Response timestamps, units, currencies, and source labels are taken from the
API response. The provider raises a typed error instead of inventing values
when a successful response is empty or malformed.

## Error Recovery

The public exception classes are:

- `AuthenticationError`: add or replace the configured API key.
- `EntitlementError`: review the current [pricing and access options](https://www.oilpriceapi.com/pricing).
- `RateLimitError`: retry after the account's rate-limit window.
- `ProviderTimeoutError`: retry the request later.
- `ResponseSchemaError`: preserve the response context and report upstream schema drift.
- `NotFoundError`: check the requested symbol mapping.

## Product Facts

Do not copy plan limits, catalog totals, source cadence, or redistribution terms
from this repository. Those facts change independently of the provider. Use the
[versioned product-facts contract](https://api.oilpriceapi.com/product-facts.json),
[API documentation](https://docs.oilpriceapi.com), and
[data-usage policy](https://www.oilpriceapi.com/legal/data-usage) when publishing
derived material.

## Development

```bash
poetry install
poetry run pytest -q
poetry build
```

To run the bounded production smoke (one latest request and one `past_year`
request) with a safe test credential:

```bash
OPENBB_OILPRICEAPI_API_KEY="..." poetry run python scripts/live_smoke.py
```

The smoke prints only the returned symbol and history record count; it never
prints the credential or request headers.

## License

[MIT](LICENSE)
