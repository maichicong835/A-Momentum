# A-Momentum

Temporal benchmark and commercial-source intelligence layer for AMZ Ideas.

A-Momentum is intentionally separate from Daily7 and A-Ver:
- **A-Momentum** measures market/query/mechanism movement and maintains quality commercial fallback pools.
- **Daily7** selects and qualifies the daily seven W/H source ideas.
- **A-Ver** resolves trademark evidence.

A-Momentum never performs trademark clearance, never selects the final Daily7 Primary 7, never acquires/focuses source images, and never mutates Google Drive, Used Ideas, or Reserve.


## Observation pipeline v0.1.1

A-Momentum keeps observations append-only and aggregates only comparable points sharing the same entity, surface, and proxy. Native platform history may contribute multiple timepoints immediately. Snapshot-only sources accumulate through `data/observations/*.json`.

The watchlist uses adaptive cadence: HOT mechanisms default to 4 hours and WARM mechanisms to 12 hours. Not-due entries are skipped. The fallback pool is maintained separately from temporal state and is never launch authorization.

A single non-commerce accelerating series is not enough for `ACCELERATING_CONFIRMED`. Confirmation requires either a strong commerce acceleration series or acceleration on at least two independent surfaces.
