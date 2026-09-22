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
