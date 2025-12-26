"""OilPriceAPI constants and symbol mappings."""

from typing import Literal

# Base URL for OilPriceAPI
OILPRICEAPI_BASE_URL = "https://api.oilpriceapi.com/v1"

# Mapping from OpenBB symbols to OilPriceAPI commodity codes
SYMBOL_MAPPING: dict[str, str] = {
    # Crude Oil
    "WTI": "WTI_USD",
    "BRENT": "BRENT_CRUDE_USD",
    "URALS": "URALS_USD",
    "DUBAI": "DUBAI_CRUDE_USD",
    # Natural Gas
    "NG": "NATURAL_GAS_USD",
    "NG_EU": "NATURAL_GAS_EU",
    "NG_UK": "NATURAL_GAS_GBP",
    # Coal
    "COAL": "COAL_USD",
    # Diesel/Gasoline
    "DIESEL_US": "DIESEL_US_NATIONAL",
    "GASOLINE_US": "GASOLINE_US_NATIONAL",
}

# Reverse mapping for transforming API responses
REVERSE_SYMBOL_MAPPING: dict[str, str] = {v: k for k, v in SYMBOL_MAPPING.items()}

# List of available symbols for validation
AVAILABLE_SYMBOLS: list[str] = list(SYMBOL_MAPPING.keys())

# Type for symbol literals (for type hints)
SymbolType = Literal[
    "WTI",
    "BRENT",
    "URALS",
    "DUBAI",
    "NG",
    "NG_EU",
    "NG_UK",
    "COAL",
    "DIESEL_US",
    "GASOLINE_US",
]
