# Initial publication audit â€” 11 November 2026

Scope: source, existing tests, configuration templates, original research prose/small measurement tables and future workflow safeguards. Remote repository was confirmed public and empty before local initialization. All publication paths are explicitly staged and checked as a complete snapshot.

Excluded: credentials/.env, environments, caches, raw ZIP/TIFFs and satellite derivatives, source PDFs/imagery/KML/GeoPackages, data/, outputs/ (except empty placeholder), work/, audit backups, model artifacts and binary/oversized files. The prior source ZIP is excluded. External satellite archives outside this checkout are not copied. No data redistribution license is inferred; third-party URLs are citations. The publication checker rejects unsupported scope, protected extensions, binary content, known secret patterns, session URLs, sensitive user/project paths and files >1 MiB or trees >10 MiB. It complements manual review and is not a proof that all secrets or rights issues can be detected.

Original documentation stays locally unchanged and ignored. Publication copies under docs/reference/ and docs/reports/ sanitize local filesystem paths, cloud-project placeholder references and a session-bearing source URL. Legacy Windows-encoded reports are decoded to UTF-8 for publication without replacing their findings. Only project-authored text and small signal/registration tables are copied; source licensed imagery/documents and geographic application datasets remain excluded. No blanket software/data license was invented.

The preexisting check_boundary.py contains a Cloud project identifier, not a key or credential; it is preserved as a legacy helper. Operational configuration remains through the existing entry points/config and excluded .env. The .env.example contains placeholders only. Commit identity uses the existing configured Git author, not a fabricated historical identity/date.

Validation: existing suite **103 passed / 0 failed / 0 skipped** (34.32 s). Regression tests are synthetic software checks, including a tiny synthetic training fixture; no real model was trained/evaluated. Scientific source files and tests remain unchanged. Scan findings are cleared by omission/sanitized publication copies, never by uploading protected assets or rewriting research claims.

Tracked pre-commit/pre-push hooks call the publication checker. They are enabled locally with core.hooksPath=.githooks; clones must configure that setting themselves. Future Codex sessions follow AGENTS.md and commit/push only completed verified tasks. Authentication/network permissions remain required; no background guarantee is implied. No force-push, history rewrite or deletion of local research files is permitted.

Actual commit/push success and file count are verified by Git and the remote at task completion; this document does not invent a commit receipt in advance.

The staged scan caught a URL-encoded session component in a publication copy; it was removed before commit. The original stays excluded. The preexisting README final blank line is preserved using a file-specific blank-at-EOF attribute exception; other whitespace checks remain enabled.
