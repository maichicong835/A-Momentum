# A-Momentum

A-Momentum is the independent temporal/commercial-intelligence provider for AMZ Ideas Daily7.

A-Momentum owns temporal sensing, comparable-series analysis and a commercial quality fallback pool. It does **not** select Daily7 Primary/Reserve portfolios, perform trademark clearance, acquire source images, run IDEA_FOCUS, mutate Google Drive, or mutate Daily7 Used/Reserve ledgers. Daily7 is a consumer; A-Ver remains the trademark evidence authority.

## Public runtime

Starting with v0.2.0, production runtime executes here. Business watchlists, query families, sanitized observations, quality-pool data and Momentum receipts may be public. The hot scheduler runs every four hours in `.github/workflows/runtime.yml`.

The first active external sensor is Google Trends native history. It removes partial rows, requires a contiguous hourly tail, aggregates non-overlapping completed 24-hour means, and requires at least three completed blocks for acceleration-capable analysis. Provider/shape failure is `SENSOR_GAP`, never zero demand. Other declared surfaces are not active collectors until machine-proven.

## Credential boundary

Public runtime does not mean public credentials. Credentials, tokens, cookies, session data, API keys, passwords, OAuth tokens, private keys and secret-bearing signed URLs must never be committed, logged, cached or uploaded as artifacts. Future authenticated sensors may receive secrets only through GitHub Actions/Environment secrets with least privilege. The current Google Trends sensor uses no credential. Google Drive credentials remain exclusively with Daily7.

## Receipt consumption

`runtime/latest/receipt.json` is a discovery pointer, not immutable Daily7 authority. Each Daily7 run must freeze the exact provider-output commit and SHA-256 of the receipt it consumes. Provider failure falls back to F5 direct Daily7 discovery.

## Google Trends wave shadow

The production Momentum Core remains the fixed-watchlist longitudinal engine. A separate **shadow-only** wave-capture path probes the open Google Trends Trending Now universe without changing production authority.

`scripts/wave_capture.py` captures public US Trending Now RSS items and keeps three query roles explicit:

- **DISCOVERY_QUERY**: the raw trend query/cluster used only to catch a market wave.
- **BRIDGE_QUERY**: commercial-expression probes such as `<trend> shirt` and `<trend> sticker`; these are supporting probes and may not redefine a longitudinal Momentum series. Raw Trending Now waves do **not** materialize these probes automatically. A separate commercial-eligibility decision must happen first, because raw waves commonly include protected entertainment, named people, politics, disasters/weather and other non-Daily7-ready topics.
- **ANCHOR_QUERY**: intentionally unassigned in shadow mode. An anchor requires later evidence and explicit promotion before a candidate may enter the production watchlist.

The shadow workflow `.github/workflows/wave-shadow.yml` has read-only repository permissions, uploads an artifact only, and is forbidden from mutating `runtime/latest` or `runtime/watchlist.json`. It does not create separate H24 or PTE engines: H24 is represented only as the wave-capture capability, while PTE-like decomposition remains a later mechanism-design function.

### Dual-wave shadow

The shadow now observes two independent Google Trends evidence tracks. **Raw Market Wave** comes from Trending Now RSS. **Merch Proxy Wave** comes from Rising related queries around the deliberately small fixed seed family `shirt`, `shirts`, and `t shirt`. The merch track is an experimental expression lens, not a sales/demand authority.

The coupler emits only `COUPLED_WAVE`, `MERCH_NATIVE_WAVE`, `RAW_ONLY_WAVE`, or `UNRESOLVED`. Coupling does not grant commercial eligibility, mechanism identity, bridge queries, anchors, or watchlist promotion. Scores from independent Google Trends requests must not be compared as absolute 0-100 magnitudes; initial learning uses presence, provider-reported rising status/rank within each seed, conservative phrase coupling, timing, and persistence.

Raw RSS capture remains independent of pytrends. The merch-proxy track currently uses pytrends experimentally and degrades to an explicit shadow sensor gap if that transport fails; such a gap never means zero demand and may not invalidate the raw-wave capture.

The existing Google Trends longitudinal sensor still uses the unofficial `pytrends` transport. That transport is treated as a fragility, not as authority; the new wave shadow does not depend on pytrends. The official Google Trends API alpha can be evaluated when access is actually available rather than assumed.

