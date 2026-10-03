# Changelog

## 0.3.1 - 2026-10-03

- Stop retrying 429s that cannot succeed. `MONTHLY_QUOTA_EXCEEDED`,
  `TRIAL_EXPIRED`, `TRIAL_LIMIT_EXCEEDED`, `EMAIL_CONFIRMATION_REQUIRED` and
  `RATE_LIMIT_EXCEEDED` now make one request and raise `RateLimitError` with the
  server's message, error code, `Retry-After` and upgrade link (#17).
- Short-lived 429s honor `Retry-After` (delta-seconds or HTTP-date) when it is
  10 seconds or less. A longer or unparseable value raises immediately instead
  of retrying early. Without the header, back off 1s then 2s. Three attempts at
  most.
- Drop the `tenacity` dependency.

## 0.3.0 - 2026-09-04

- Identify latest and historical requests as `oilpriceapi-openbb/<version>` and
  send canonical `X-SDK-*` attribution headers without exposing credentials.
- Add the `past_year` historical period.
- Keep symbol support deliberately curated to the ten documented OpenBB-style
  mappings. The API catalog changes independently, while OpenBB query choices
  must remain deterministic; new mappings will be reviewed and released here.
- Add a bounded two-request production smoke for latest and `past_year` history.

This release advances the attribution work tracked in
[oilpriceapi-api#4592](https://github.com/OilpriceAPI/oilpriceapi-api/issues/4592)
and [oilpriceapi-api#6434](https://github.com/OilpriceAPI/oilpriceapi-api/issues/6434).
