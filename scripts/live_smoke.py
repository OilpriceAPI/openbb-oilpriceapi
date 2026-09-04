"""Bounded two-request production smoke for an installed provider release."""

import asyncio
import os

from openbb_oilpriceapi.models import OilHistoricalFetcher, OilPriceAPIFetcher


async def main() -> None:
    api_key = os.environ.get("OPENBB_OILPRICEAPI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENBB_OILPRICEAPI_API_KEY to run the live smoke.")

    credentials = {"api_key": api_key}
    latest = await OilPriceAPIFetcher.fetch_data({"symbol": "WTI"}, credentials)
    history = await OilHistoricalFetcher.fetch_data(
        {"symbol": "WTI", "period": "past_year"}, credentials
    )
    if not latest or not history:
        raise RuntimeError("OilPriceAPI returned an empty successful response.")

    print(
        "OpenBB live smoke passed: "
        f"latest={latest[0].symbol}, history_records={len(history)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
