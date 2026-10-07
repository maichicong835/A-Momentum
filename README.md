# A-Momentum

A-Momentum is the independent temporal/commercial-intelligence provider for AMZ Ideas Daily7.

A-Momentum owns temporal sensing, comparable-series analysis and a commercial quality fallback pool. It does **not** select Daily7 Primary/Reserve portfolios, perform trademark clearance, acquire source images, run IDEA_FOCUS, mutate Google Drive, or mutate Daily7 Used/Reserve ledgers. Daily7 is a consumer; A-Ver remains the trademark evidence authority.

## Public runtime

Starting with v0.2.0, production runtime executes here. Business watchlists, query families, sanitized observations, quality-pool data and Momentum receipts may be public. The hot scheduler runs every four hours in `.github/workflows/runtime.yml`.

The first active external sensor is Google Trends native history. It removes partial rows, requires a contiguous hourly tail, aggregates non-overlapping completed 24-hour means, and requires at least three completed blocks for acceleration-capable analysis. Provider/shape failure is `SENSOR_GAP`, never zero demand. Other declared surfaces are not active collectors until machine-proven.

### Measurement identity (M1)

Each production watch entry now declares a stable Google Trends `anchor_query` and `anchor_proxy_id`. The first query in the ordered query family is the anchor; later queries are availability fallbacks with their own proxy identity. A fallback success may provide a usable current signal, but it may not silently redefine the anchor. Native rolling-window timestamps remain provenance, not proxy identity.

Receipts expose whether each mechanism's current measurement truth is based on `PRIMARY_ANCHOR`, `FALLBACK_PROXY`, or `ANCHOR_GAP`. When two mechanisms share the same anchor or current query proxy, that sharing is machine-visible and must not be interpreted as independent evidence.

### Fair slot allocation shadow (M2a)

M2a is currently a **shadow/synthetic-only** capacity experiment. `scripts/slot_allocator.py` proves behavior for a due universe larger than the 15-query budget without changing the production watchlist or wiring the allocator into `.github/workflows/runtime.yml`.

The shadow allocator ranks due entries by normalized overdue age (`elapsed_hours / cadence_hours`), prioritizes never-observed entries, and uses a stable ID only as a deterministic tie-break. Overflow is `DEFERRED_BY_ALLOCATION`: it is neither `NOT_DUE` nor `SENSOR_GAP`, and it may not advance evidence freshness. Production wiring remains blocked until the first scheduled M1 publication is machine-proven; CORE/EXPLORATION quotas are intentionally not defined in M2a.

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

The coupler emits only `COUPLED_WAVE`, `MERCH_NATIVE_WAVE`, `RAW_ONLY_WAVE`, or `UNRESOLVED`. Coupling does not grant commercial eligibility, mechanism identity, bridge queries, anchors, or watchlist promotion. Scores from independent Google Trends requests must not be compared as absolute 0-100 magnitudes; initial learning uses presence, provider-reported rising status/rank within each seed, conservative phrase coupling, timing, and persistence. Cross-seed duplicates are grouped into one normalized merch core while every original seed/rank/value observation is preserved as evidence, preventing the `shirt`/`shirts`/`t shirt` family from inflating apparent wave counts. `COUPLED_WAVE` requires exact normalized core equality; partial phrase or named-entity overlap is `UNRESOLVED`, because sharing an entity does not prove that the raw-news phenomenon and merch-expression phenomenon are the same wave.


### Wave Shadow trigger/request budget

Wave Shadow now separates code validation from live market-provider access. `push` runs execute credential scanning, local self-tests and unit tests only; they do **not** call Google Trends live endpoints. Scheduled Wave Shadow provider capture is currently paused after the completed S-wave cross-snapshot proof. While paused, live Raw/Merch/S capture is available only through explicit `workflow_dispatch`; `push` remains validation-only.

This prevents routine code merges from consuming the same external-provider request budget used for actual discovery and reduces self-induced throttling. A successful push validates code/contract only and is not a fresh market observation. While the schedule remains paused, explicitly dispatched live artifacts are the only source of fresh Wave Shadow market evidence; historical scheduled artifacts remain frozen evidence for the completed proofs.

### Merch Proxy rate-limit transport

The Merch Proxy remains an experimental Google Trends Related/Rising Queries sensor, but its transport is deliberately rate-shaped. The fixed seed family is sent in one batched payload so token/cookie setup is shared instead of repeated per seed. Related-query widgets are then fetched independently with spacing, so a later seed failure cannot erase earlier seed data.

HTTP 429 opens a circuit instead of triggering an immediate retry storm on the same egress. A batch-token 429 may receive one delayed build retry; a related-query 429 stops further seed requests for that run and records the remaining seeds as `RATE_LIMIT_CIRCUIT_OPEN`. Any successful seeds remain usable as partial shadow evidence. Rate limiting is a sensor gap, never zero demand and never proof that no Rising queries exist.

This hardening reduces request footprint but does not make pytrends authoritative. pytrends remains archived/unofficial, and hosted-runner network variability remains a transport risk. The seed family is not expanded merely to compensate for transport failure.

### Merch Proxy transport acceptance gate

Every live Merch Proxy artifact classifies transport health as one of `RECOVERED_WITH_DATA`, `PARTIAL_WITH_DATA`, `THROTTLED`, `PASS_NO_RISING_DATA`, `PARTIAL_NO_RISING_DATA`, or `OTHER_SENSOR_GAP`. The historical field `bridge_experiment_input_ready` is retained only for backward-compatible transport/evidence readiness; the current multi-radar pipeline does **not** use it as an admission gate and Commercial Bridge is deferred. It is not commercial eligibility, launch authorization, or proof of demand.

### M opportunity intake sublayer

The R/M Dual-Wave sublayer does **not** wait for Raw and Merch waves to intersect. Every unique M core can enter discovery immediately; R remains parallel attention/context evidence. This M intake is now one input to the broader M ∪ S Opportunity Union rather than the sole final intake.


### Independent sticker-native S-wave and M ∪ S union

Sticker is no longer used as a confirmation bridge for M. A separate **S-wave** radar queries the deliberately small sticker-native seed family `sticker`, `stickers`, and `vinyl sticker` using the same hardened Related/Rising transport. Its purpose is to discover category-native sticker opportunities that may never appear in shirt-expression space.

M and S are independent discovery lanes. The current admission rule is `M OR S`, not `M AND S`. Upstream redundancy is allowed because missing an opportunity is more expensive than carrying duplicate evidence. Dedupe happens only when the normalized opportunity core is exactly equal; ambiguous partial overlap is not merged. Sticker normalization is intentionally conservative: only a trailing `sticker`/`stickers` format token may be removed. Prefix or middle occurrences are preserved so names such as `Sticker Mule` cannot collapse into a misleading generic core. A unique opportunity therefore carries one of three origin states: `M_ONLY`, `S_ONLY`, or `M_S_MULTI_RADAR`, while retaining the original per-radar seed/query/rank evidence.

The R/M coupler is preserved as an evidence sublayer rather than rewritten. After R/M coupling, the workflow unions M evidence with S evidence, then sends the deduped union through the existing structural triage, semantic resolution, and mechanism-abstraction layers. Neither radar confirms the other, neither grants commercial eligibility, and neither can auto-generate creative, bridge queries, anchors, watchlist entries, or Daily7 selections.

To protect provider request budget, M and S remain separate three-seed batches with a pause between them; a sensor gap in one radar may not erase usable evidence from the other. Push runs remain validation-only and make no live provider calls. Commercial Bridge is intentionally deferred because open sticker-native discovery has higher information yield than re-querying sticker space merely to confirm an M observation.

### Structural triage shadow

M-primary intake now receives a conservative structural triage before any mechanism decomposition. The triage recognizes only a few high-confidence query structures: phrase-led expression, cause/awareness expression, obvious apparel/product configuration demand, and local purchase/navigation intent. Everything else defaults to `HOLD_SEMANTIC_REVIEW`.

This is intentionally not named-entity recognition, property/title detection, trademark clearance, commercial eligibility, or idea generation. A query such as `dolly parton`, `foam finger`, or `creation of adam` is not force-classified from lexical shape alone; it remains unresolved until a later semantic evidence layer exists. A structural PASS only means the query shape is compatible with expression-oriented decomposition. It does not mean the idea is safe, ownable, commercially validated, or launchable.


### Provenance-first semantic resolution

Only `HOLD_SEMANTIC_REVIEW` items are sent to a lightweight Wikidata metadata resolver. Wikidata is used only to answer “what exact entity/concept does this query name?” and never contributes market demand or trend strength. Resolution still starts from exact normalized label/alias evidence. When several exact matches exist, the resolver may disambiguate only with unique canonical metadata: either one unique primary label match or one unique English-Wikipedia sitelink among the exact candidates. Otherwise it remains unresolved. Provider throttling is recorded as a metadata gap, never semantic absence.

Resolved metadata keeps QID, label, description, match basis, and concept URL as provenance. The resolver may distinguish named people, creative works/properties, organizations/brands, events, cultural symbols/objects, product/physical objects, and generic concepts/themes. This still does not perform trademark/copyright clearance, commercial eligibility, or automatic mechanism generation. Cultural/concept metadata may only become eligible for later human/machine mechanism review, not automatic decomposition.


### Mechanism decomposition shadow

Only evidence that has already received explicit mechanism-review permission may enter mechanism decomposition. Structural passes currently support phrase-expression and cause-awareness structures; semantic resolution may additionally admit cultural-symbol/object or generic-concept/theme evidence when that resolver explicitly sets `mechanism_review_allowed=true`.

The output is a **mechanism hypothesis**, not a production mechanism. It keeps the source query only as provenance and abstracts it into a coarse mechanism family, expression mode, social function, and transferable unit. Source wording or iconography may not be reused as generated product copy. The layer performs no trademark/copyright/property clearance, commercial eligibility, sticker idea generation, bridge-query materialization, anchor assignment, watchlist promotion, or Daily7 selection.

Raw RSS capture remains independent of pytrends. The merch-proxy track currently uses pytrends experimentally and degrades to an explicit shadow sensor gap if that transport fails; such a gap never means zero demand and may not invalidate the raw-wave capture.

The existing Google Trends longitudinal sensor still uses the unofficial `pytrends` transport. That transport is treated as a fragility, not as authority. Raw Wave RSS capture does not depend on pytrends; only the experimental Merch Proxy shadow currently does. The official Google Trends API alpha can be evaluated when access is actually available rather than assumed.

