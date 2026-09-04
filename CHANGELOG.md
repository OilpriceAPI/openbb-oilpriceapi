# Changelog

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
