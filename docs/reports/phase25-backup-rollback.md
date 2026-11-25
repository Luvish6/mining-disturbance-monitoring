# Pre-MineChange-India backup and rollback safeguard

Verified 2026-11-25. No Phase 25B implementation, data acquisition or model fitting was performed.

## Stable code and branches

- Last stable pre-Phase-25 commit: `08604dea4fe39641ea32ebda8a37532669b52933` (Planet licensing fixes included).
- Annotated stable tag: `pre-minechange-india`; tag object `5e90e7c550490165e26c62187ce8c96e89761946`, resolving to the commit above. Pushed and verified against the remote peeled reference. Never retarget or delete it.
- Existing branch `phase22-label-sources` is preserved at `d0b6dd1ac7c6771f3bfccf11c4353cf1a77b7574`. That later commit adds only Phase 25A documentation; source, scripts, tests, frontend and config match the stable tag exactly.
- Separate development branch `phase25-minechange-india` was created from the existing branch and pushed. All future Phase 25 work stays here. No merge to the preserved branch/main without explicit approval.
- Source and copied Git object stores passed `git fsck --full --no-dangling`. A private `repository.bundle` contains all refs and passed `git bundle verify`. Existing dangling objects were preserved, not pruned.

## Complete private local snapshot

The backup is outside the repository and OneDrive on D:, under the private ResearchBackups/mining-monitoring directory. The exact location and commands are in the user's final task response and the backup's `RESTORE-INSTRUCTIONS.md`. No backup payload, per-file manifest, credentials or licensed imagery is published.

Scope: the entire project parent, including the checkout and `.git`, data, ignored outputs/results, checkpoints, original Planet/LISS-IV ZIPs, delivery/extracted files, outreach drafts, virtual environment, node dependencies and parent project settings. Files outside this known project parent (such as OS credential stores) are not claimed to be backed up. No source reparse points were present. Folder access is restricted to the current account, SYSTEM and Administrators, with inheritance disabled at the backup root.

**72,005 files / 9,106 directories / 7,918,850,848 bytes (7.375 GiB)** were copied. Required capacity was checked before copying against approximately 337.74 GB free on D:, with a further 10 GiB reserve. Every source file and its copied counterpart was compared by size and SHA-256. Exact file/directory inventories and source size/mtime snapshots matched before and after. **Zero checksum mismatches, zero missing files, source mutation check PASS.** Copy and verification took 433.62 seconds. Robocopy exit 1 means files copied successfully, not failure.

- Private `files-sha256.csv`: relative paths, sizes, source mtimes and per-file SHA-256.
- Manifest SHA-256: `fac35b9b16303fdb2cb375af76f3dbba872e4c16c2b1cf30be5cda4b900de7c4`.
- Private `source-inventory.json` SHA-256: `ebebe613a92f3bee3f2da351de7f41a86ff21ba95148c8ea28d303d978012d28`.
- Private `verification.json`, `SHA256SUMS`, copy log, standalone re-verifier and Git bundle retain additional verification evidence.
- [Sanitized receipt](phase25-backup-verification.json) records aggregate verification only.

Frozen TEST files were handled solely as opaque backup bytes for copying/hashing. No raster decoding, image viewing, label interpretation, prediction, fitting or scoring occurred, and their contents were not modified. This checksum operation is not scientific access/admission or permission for later TEST evaluation.

**Limitation:** D: and C: are partitions on physical disk 0. This is a verified local rollback snapshot, not off-device disaster recovery. An additional private/encrypted copy on a physically separate drive is recommended before relying on it against disk failure.

## Phase 25 isolation

Reserved ignored directories: `outputs/phase25/datasets/`, `models/`, `experiments/`, `receipts/` and `qa/`. Use a new versioned run directory for every artifact and fail if a target already exists. Never overwrite historical datasets, cached imagery, masks, normalization, checkpoints or result receipts. Existing `outputs/phase25a_feasibility/` also remains unchanged; it was included in the snapshot. New directory reservation occurred only after full backup verification.

The backup is a point-in-time snapshot taken at d0b6dd1 with the new tag/branch already created. This safeguard documentation and later Phase 25 artifacts are intentionally not retroactively inserted into the snapshot. A new backup/version is needed for later recovery points. No automatic merge, reset, cleanup or mutation of the old branch is allowed.

## Exact, non-destructive full rollback

Prefer restoring into a fresh empty directory while retaining the live checkout. Stop relevant live development processes before deliberately switching code. The private `RESTORE-INSTRUCTIONS.md` supplies concrete local paths. These publication-safe commands request those paths rather than embedding private source locations:

```powershell
$backup = (Resolve-Path -LiteralPath (Read-Host 'Private backup root')).Path
$receipt = Get-Content -LiteralPath "$backup\verification.json" -Raw | ConvertFrom-Json
if ($receipt.status -ne 'VERIFIED') { throw 'Backup is not verified' }
$manifestHash = (Get-FileHash -LiteralPath "$backup\files-sha256.csv" -Algorithm SHA256).Hash.ToLowerInvariant()
if ($manifestHash -ne 'fac35b9b16303fdb2cb375af76f3dbba872e4c16c2b1cf30be5cda4b900de7c4') { throw 'Manifest changed' }
py -3 "$backup\backup_verify.py" --verify
if ($LASTEXITCODE -ne 0) { throw 'Backup file verification failed' }
$restore = Read-Host 'New empty restore directory outside the repository and OneDrive'
if (Test-Path -LiteralPath $restore) { throw 'Choose a new destination; do not overwrite' }
robocopy "$backup\project_parent" $restore /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ
if ($LASTEXITCODE -ge 8) { throw 'Restore copy failed' }
# Verify the restored file bytes before Git intentionally changes tracked code.
foreach ($entry in (Import-Csv -LiteralPath "$backup\files-sha256.csv")) {
    $restoredFile = Join-Path $restore $entry.path
    if ((Get-FileHash -LiteralPath $restoredFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
        throw "Restored checksum mismatch: $($entry.path)"
    }
}
$repo = Join-Path $restore 'mining_monitor_phase1'
git -C $repo switch --detach pre-minechange-india
if ($LASTEXITCODE -ne 0) { throw 'Stop and preserve state; inspect checkout conflict' }
$restoredHead = git -C $repo rev-parse HEAD
if ($restoredHead -ne '08604dea4fe39641ea32ebda8a37532669b52933') { throw 'Wrong stable commit' }
```

The restored snapshot contains all ignored historical data. Detaching at the tag restores tracked stable code without overwriting the original working directory. A Windows virtual environment or npm launcher may contain absolute paths: check the installed base interpreter and recreate dependencies only inside the fresh restore if relocation requires it. No environment installation was attempted here. A code-only switch in the existing checkout does not restore datasets and should be attempted only after separately preserving dirty/untracked work.

Never use `reset --hard`, `git clean`, overwrite a live directory, force-push or merge experimental work as a rollback shortcut. Verification failure means STOP. The stable tag, original branch, current checkout and private snapshot are separate safeguards.

## Validation and next boundary

Backup file hashes/inventory, source immutability, private ACLs, Git object integrity, bundle integrity, ignored Phase 25 paths and remote refs were checked. Documentation/schema checks and the staged publication audit passed; no unnecessary model/imagery tests were run. A full restore was not executed: the actual copied bytes, file sets and Git stores were verified, and non-destructive restore commands are documented. **Phase 25B remains NOT STARTED.** Its existing approval boundary and separate acquisition/training approvals remain in force.
