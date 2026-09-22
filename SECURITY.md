# Security and data-boundary policy

A-Momentum is a public code repository. It must contain only generic engine code, schemas, tests, documentation, and synthetic fixtures.

Do not commit:
- production watchlists or query families;
- proprietary candidate/mechanism keys;
- commercial quality pools;
- market observations or source references;
- marketplace object identifiers tied to a private strategy;
- credentials, tokens, cookies, session data, API keys, or account identifiers.

Production runtime data must be supplied by a private consumer repository at execution time. Public examples are synthetic and are not market evidence.

Historical commits created before the code-only boundary may contain earlier runtime examples/data. Deleting files from current main does not erase Git history; a history rewrite is required if complete historical removal is desired.
