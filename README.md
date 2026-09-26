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

## P1 Daily7 commerce observation handshake

P1 adds a strict contract for sanitized commerce observations produced by immutable Daily7 runs. It does not let the public A-Momentum runtime read the private Daily7 repository, does not transfer Daily7 credentials, and does not parse historical free-form marketplace prose into numeric time series.

Accepted P1 records must bind the exact Daily7 commit and run path, carry a machine-observed numeric value and timestamp, and use a stable proxy. Listing favorites/review counts remain MARKET_OBJECT evidence and may not automatically promote a linked mechanism. Mechanism-level independent-listing counts are supporting-only. New mechanism keys cannot enter through this handshake unless they already exist in the current A-Momentum watchlist.

The contract and adapter are intentionally **runtime-inactive** until a sanitized export transport is independently machine-proven. Until that activation gate is satisfied, production runtime remains Google-Trends-only and Daily7 continues to consume A-Momentum through the existing fail-soft provider boundary.

