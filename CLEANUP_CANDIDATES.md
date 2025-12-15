**Cleanup candidates & plan**

But: Do NOT delete anything permanently without review. This document lists safe candidates to archive first.

Scope (recommended):
- Move to `archive/` (safe, reversible):
  - All `*.md` except: `README.md`, `QUICK_START.md`, `DEPLOYMENT_CHECKLIST.md`
  - All `*.txt` (commit messages, route_check, etc.)
  - All `*.log`, `*.old`, `*.bak`, `*.sample`

Excluded (do NOT remove):
- All `*.py` in root and `app.py`, `database.py`, templates, `static/` assets, Stripe/checkout code, API routes and any file referenced by code.

Procedure (safe):
1. Run `python scripts/safe_archive_candidates.py` and confirm.
2. Review `archive/<timestamp>/ARCHIVE_REPORT.txt`.
3. Deploy to staging and run smoke tests (add-to-cart → cart → checkout) with monitoring for errors.
4. If everything is OK after 7–30 days, permanently delete the archive folder.

Why archive rather than delete:
- Preserves a reversible safety net. Immediate deletion risks breaking integrations if a file was referenced unexpectedly.

If you want, I can:
- Run the archival script here (requires confirmation), or
- Produce the `git rm` commands to permanently remove the archived files after your review.
