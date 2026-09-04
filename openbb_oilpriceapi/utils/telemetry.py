"""Request attribution shared by every OilPriceAPI fetcher."""

from importlib.metadata import version


SDK_NAME = "oilpriceapi-openbb"
SDK_VERSION = version("openbb-oilpriceapi")


def build_request_headers(api_key: str) -> dict[str, str]:
    """Build authenticated headers without copying credentials into attribution."""
    return {
        "Authorization": f"Token {api_key}",
        "Accept": "application/json",
        "User-Agent": f"{SDK_NAME}/{SDK_VERSION}",
        "X-SDK-Name": SDK_NAME,
        "X-SDK-Version": SDK_VERSION,
        "X-SDK-Language": "python",
        "X-Client-Type": "sdk",
    }
