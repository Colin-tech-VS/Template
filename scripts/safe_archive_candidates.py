#!/usr/bin/env python3
"""
Safe archival script for non-critical documentation and ephemeral files.

This script WILL NOT delete files. It moves matched candidates into
an `archive/<timestamp>/` folder at the project root so you can review
and purge later.

Usage:
    python scripts/safe_archive_candidates.py

By default it targets:
  - *.md (except README.md, QUICK_START.md, DEPLOYMENT_CHECKLIST.md)
  - *.txt
  - *.log
  - *.old, *.bak, *.sample

It will skip folders: `templates`, `static`, `venv`, `.git`, and any
Python source files. Review the generated report before permanent deletion.
"""
from __future__ import annotations
import os
import shutil
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARCHIVE_DIR = os.path.join(ROOT, 'archive', datetime.utcnow().strftime('%Y%m%d_%H%M%S'))

# Keeplist for markdown files we want to preserve in root
MD_KEEP = {'README.md', 'QUICK_START.md', 'DEPLOYMENT_CHECKLIST.md'}

PATTERNS = ['.md', '.txt', '.log', '.old', '.bak', '.sample']

EXCLUDE_DIRS = {'.git', 'venv', 'archive', '__pycache__'}

def is_candidate(path: str) -> bool:
    if os.path.isdir(path):
        return False
    rel = os.path.relpath(path, ROOT)
    if any(part in EXCLUDE_DIRS for part in rel.split(os.sep)):
        return False
    _, ext = os.path.splitext(path)
    if ext.lower() in PATTERNS:
        base = os.path.basename(path)
        if ext.lower() == '.md' and base in MD_KEEP:
            return False
        return True
    return False

def gather_candidates() -> list[str]:
    candidates = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Skip excluded dirs early
        parts = set(dirpath.split(os.sep))
        if parts & EXCLUDE_DIRS:
            continue
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if is_candidate(p):
                candidates.append(p)
    return candidates

def archive_files(files: list[str]):
    if not files:
        print('No candidates found.')
        return
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    report = []
    for f in files:
        rel = os.path.relpath(f, ROOT)
        dest = os.path.join(ARCHIVE_DIR, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(f, dest)
        report.append((rel, dest))
        print(f'Moved: {rel} -> archive/{os.path.relpath(dest, os.path.join(ROOT, "archive"))}')

    # Write a report
    report_path = os.path.join(ARCHIVE_DIR, 'ARCHIVE_REPORT.txt')
    with open(report_path, 'w', encoding='utf-8') as fh:
        fh.write('Archived files report\n')
        fh.write(f'Timestamp: {datetime.utcnow().isoformat()}Z\n\n')
        for rel, dest in report:
            fh.write(f'{rel} -> {dest}\n')

    print('\nArchive complete. Review the archive folder before permanent deletion:')
    print(ARCHIVE_DIR)

if __name__ == '__main__':
    candidates = gather_candidates()
    print(f'Found {len(candidates)} candidate(s) for archival:')
    for c in candidates:
        print(' -', os.path.relpath(c, ROOT))
    confirm = input('\nMove these files to archive (y/N)? ')
    if confirm.lower() == 'y':
        archive_files(candidates)
    else:
        print('Aborted. No files moved.')
