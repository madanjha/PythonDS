# Release bulletin verification report

- **Bulletin:** `sample/release_bulletin.pdf`
- **Change set:** dirs sample/before -> sample/after
- **Files changed:** 8  |  **Bulletin file mentions:** 8
- **Result:** DISCREPANCIES FOUND

| Bucket | Count |
|---|---|
| Missing in bulletin (changed but not documented) | 2 |
| Missing in files (documented but not changed) | 3 |
| Change type mismatch | 1 |
| Ambiguous mentions | 1 |
| Bulletin items without a file reference | 1 |
| Documented and matching | 3 |

## Missing in bulletin (changed but not documented) (2)

| File | Status | Bulletin line (page) | Match | Reason |
|---|---|---|---|---|
| config/settings.yaml | modified | - | - | File was modified but the bulletin does not mention it. |
| src/utils/helpers.py | modified | - | - | File was modified but the bulletin does not mention it. |

## Missing in files (documented but not changed) (3)

| File | Status | Bulletin line (page) | Match | Reason |
|---|---|---|---|---|
| session.py<br>candidates: src/auth/session.py | - | - Updated session.py to shorten the session TTL. (p.1) | - | 'session.py' exists in the tree (src/auth/session.py) but did NOT change in this release. |
| notifications/email_sender.py | - | - Added notifications/email_sender.py for alert e-mails. (p.1) | - | 'notifications/email_sender.py' does not exist in the file tree and no matching change was found. |
| docs/README.md<br>candidates: docs/README.md | - | docs/README.md Updated install steps DOC-7 (p.1) | - | 'docs/README.md' exists in the tree (docs/README.md) but did NOT change in this release. |

## Change type mismatch (1)

| File | Status | Bulletin line (page) | Match | Reason |
|---|---|---|---|---|
| src/billing/invoice.py | modified | src/billing/invoice.py Added tax support BILL-42 (p.1) | exact 1.0 | Bulletin says 'added', file was actually 'modified'. |

## Ambiguous mentions (1)

| File | Status | Bulletin line (page) | Match | Reason |
|---|---|---|---|---|
| candidates: mobile/app/config.js, web/app/config.js | - | - Updated config.js to point to API v2. (p.1) | path-suffix 0.95 | 'config.js' matches 2 changed files (path-suffix); confirm which file is meant. |

## Bulletin items without a file reference (1)

| File | Status | Bulletin line (page) | Match | Reason |
|---|---|---|---|---|
| - | - | - Improved dashboard load performance. (p.1) | - | Bulletin item names no file; verify manually against the diffs. |

## Documented and matching (3)

| File | Status | Bulletin line (page) | Match | Reason |
|---|---|---|---|---|
| src/auth/login.py | modified | - Fixed login timeout in src/auth/login.py (30s to 120s). (p.1) | exact 1.0 | Bulletin mention 'src/auth/login.py' matched (exact). |
| src/reports/export_csv.py | added | - Added CSV export module export_csv.py for reports. (p.1) | path-suffix 0.95 | Bulletin mention 'export_csv.py' matched (path-suffix). |
| src/legacy/old_api.py | removed | - Removed deprecated src/legacy/old_api.py. (p.1) | exact 1.0 | Bulletin mention 'src/legacy/old_api.py' matched (exact). |
