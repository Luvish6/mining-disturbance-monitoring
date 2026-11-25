# Phase 25D.2 — Approved ANTLR build and resolver stop

2026-11-25. Existing Python 3.12.10 isolated venv and cumulative ledger reused. No recreation, package installation, checkpoint download, GPU smoke, dataset modification or TEST payload access occurred.

Available RAM passed at 8.002 GiB and 8.031 GiB at setup entry; GPU free 7,956 MiB of 8,188 MiB. C: free about 26 GiB; D: about 307 GiB. Verified backup inventory fingerprint/status, immutable 80-patch manifest SHA and absent acquisition lock passed. Backup remains on the same physical disk and is not off-device protection.

## Approved one-time build

Official PyPI 4.9.3 metadata authenticated the 117,034-byte ANTLR source distribution: SHA-256 `f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b`. Declarative setup metadata and 56 Python runtime files were inspected. A pure-Python wheel was assembled without executing setup.py, invoking external build dependencies or compiling native code. Original runtime file bytes were retained; only the packaged CLI shebang was standardized. Archive CRC, file content and RECORD hashes were checked.

Wheel: 144,348 bytes; SHA-256 `f81e5d48980b5f512d2d1859ab9455ed7807c1a6651c0814f4a6c098111f4a56`. Source, wheel and private receipt remain in the isolated D: cache. Existing receipt prevents rebuilding; hash-bound local serving permits only this named wheel. All other resolution remains wheel-only with --no-build.

## Stop and correction

The resolver stopped before installation because its HTTP HEAD request received 501 from the loopback proxy. This is a confirmed proxy transport defect, not model incompatibility. Added restricted local-wheel HEAD support and offline tests; did not rerun setup after this failure, in accordance with the immediate-stop instruction. Dependency resolution and installation remain incomplete.

Eight focused offline tests passed, including altered-wheel rejection, path restriction and HEAD handling without external transfer. Cumulative dependency body bytes: 73,254,635; conservatively charged bytes including reserved headers: 78,071,531, below 12 GiB. Model transfer: 0 bytes. Counters were not reset. Peak GPU/process smoke memory, model outputs, masks and frozen gradients remain UNMEASURED.

Next action: resume the same setup command after resource recheck, reusing the approved wheel, venv, cache and remaining ledger budgets. Only after successful dependency installation may the pinned Tiny download and single synthetic GPU smoke proceed under the original limits. No research training is authorized. Indian supervised training remains NO-GO; candidates UNKNOWN; operational alerts zero.
