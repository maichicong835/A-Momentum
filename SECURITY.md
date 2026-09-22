# Security and credential-isolation policy

A-Momentum is public and may run production schedules and publish sanitized business data. The hard private boundary is credentials and secret-bearing session material.

Never commit, log, cache or upload as an artifact: passwords; API keys; personal access tokens; OAuth access/refresh tokens or client secrets; cookies/session IDs/authorization headers; private/signing keys; secret-bearing signed URLs; Google Drive/email credentials.

The current Google Trends runtime requires no credential.

Future authenticated sensors must use GitHub Actions/Environment secrets with least privilege, must not execute secret-bearing logic from untrusted pull-request content, and must never emit secret values to JSON, logs, artifacts, caches, URLs or commits. If exposure is suspected, revoke/rotate first; repository cleanup alone is not sufficient.

`scripts/security_scan.py` is defense in depth, not a guarantee against every possible secret format. A-Momentum has no Google Drive authority.
