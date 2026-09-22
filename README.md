# A-Momentum

Temporal benchmark engine for market/query/mechanism movement. This public repository is intentionally **code-only**.

A-Momentum accepts runtime observations, watchlists and fallback-pool data supplied by a private consumer repository. The public repository stores only generic engine code, schemas, tests, documentation and synthetic fixtures.

A-Momentum never performs trademark clearance, never selects a final portfolio, never acquires source images, and never mutates downstream delivery systems.

## Observation pipeline

Observations are append-only and aggregate only when they share the same entity, surface and proxy. Native platform history may contribute multiple timepoints immediately; snapshot-only production data is accumulated outside this repository and passed to the builder through CLI paths.

A single observation never proves growth. Two comparable timepoints may establish velocity; three are required before acceleration can be measured. A single non-commerce accelerating series is not enough for `ACCELERATING_CONFIRMED`; confirmation requires either a strong commerce acceleration series or acceleration on at least two independent surfaces.

## Public/private boundary

Production watchlists, proprietary query families, commercial quality pools, market observations, source references, marketplace object identifiers tied to a private strategy, credentials and session data must not be committed here. See `SECURITY.md`.

The files under `examples/` are synthetic fixtures only and are not market evidence.
