"""Fetch one source-timestamped OilPriceAPI record through the OpenBB fetcher."""

import asyncio
import json
import os
import sys

from openbb_oilpriceapi.models import OilPriceAPIFetcher


async def main() -> None:
    api_key = os.environ.get("OPENBB_OILPRICEAPI_API_KEY")
    if not api_key:
        raise SystemExit(
            "Set OPENBB_OILPRICEAPI_API_KEY. Manage keys at "
            "https://www.oilpriceapi.com/auth/signup"
        )

    symbol = sys.argv[1] if len(sys.argv) > 1 else "BRENT"
    records = await OilPriceAPIFetcher.fetch_data(
        {"symbol": symbol}, {"api_key": api_key}
    )
    print(json.dumps(records[0].model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
