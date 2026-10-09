#!/usr/bin/env python3
"""
release_bulletin_verifier.py

Compares the files that actually changed in a release against the files/
changes mentioned in a release-bulletin PDF, and reports discrepancies in
both directions.

Change source (pick ONE):
    --before-dir DIR --after-dir DIR      snapshot-vs-snapshot (hash compare)
    --repo DIR --from-ref REF --to-ref REF   git diff between two refs

Usage:
    python release_bulletin_verifier.py \
        --before-dir ./release_9.2 --after-dir ./release_9.3 \
        --bulletin ./release_9.3_bulletin.pdf \
        --out report.json --out-md report.md

    python release_bulletin_verifier.py \
        --repo . --from-ref v9.2 --to-ref v9.3 \
        --bulletin ./release_9.3_bulletin.pdf
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


# --------------------------------------------------------------------------
# 1. Change detection
# --------------------------------------------------------------------------
def hash_file(path, block=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root, ignore_dirs=(".git", "node_modules", "__pycache__", ".venv")):
    root = Path(root)
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for fname in filenames:
            p = Path(dirpath) / fname
            rel = str(p.relative_to(root)).replace(os.sep, "/")
            try:
                out[rel] = hash_file(p)
            except OSError as exc:
                print(f"  ! skipping unreadable file {rel}: {exc}", file=sys.stderr)
    return out


def diff_snapshots(before_dir, after_dir):
    before, after = snapshot(before_dir), snapshot(after_dir)
    changes = {}
    for path in sorted(set(before) | set(after)):
        if path not in before:
            changes[path] = "added"
        elif path not in after:
            changes[path] = "removed"
        elif before[path] != after[path]:
            changes[path] = "modified"
    return changes


def diff_git(repo, from_ref, to_ref):
    result = subprocess.run(
        ["git", "-C", repo, "diff", "--name-status", f"{from_ref}..{to_ref}"],
        capture_output=True, text=True, check=True,
    )
    status_map = {"A": "added", "D": "removed", "M": "modified"}
    changes = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        kind = status_map.get(status[0], f"other({status})")
        if status[0] == "R" and len(parts) == 3:  # rename: old\tnew
            changes[parts[2]] = "renamed_from:" + parts[1]
            continue
        changes[path] = kind
    return changes


# --------------------------------------------------------------------------
# 2. Bulletin extraction
# --------------------------------------------------------------------------
PATH_RE = re.compile(r"[\w\-./\\]+\.[A-Za-z][A-Za-z0-9]{0,4}\b")  # crude "looks like a filename" matcher


def extract_pdf_text(pdf_path):
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed: pip install pypdf")
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_bulletin_items(text):
    """
    Returns a list of {"line": raw bullet/line text, "paths": [filenames found in it]}.
    Splits on bullets, numbered items, and newlines; keeps the raw line so the
    Agent can read full context even when no explicit filename is present.
    """
    raw_lines = re.split(r"\n|•|(?:^|\n)\s*[-*]\s+|\n\d+[.)]\s+", text)
    items = []
    for line in raw_lines:
        line = line.strip()
        if len(line) < 3:
            continue
        paths = PATH_RE.findall(line)
        items.append({"line": line, "paths": paths})
    return items


# --------------------------------------------------------------------------
# 3. Cross-verification
# --------------------------------------------------------------------------
def basename_key(path):
    return Path(path).name.lower()


def fuzzy_match(name, candidates, cutoff=0.86):
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def cross_verify(changes, bulletin_items):
    changed_paths = list(changes.keys())
    changed_basenames = {basename_key(p): p for p in changed_paths}

    bulletin_mentions = {}   # changed_path -> list of bulletin lines that referenced it
    phantom_entries = []     # bulletin lines whose mentioned path(s) don't match any change
    ambiguous = []           # bulletin lines where a mentioned name matches >1 changed file

    for item in bulletin_items:
        if not item["paths"]:
            continue
        for mentioned in item["paths"]:
            key = basename_key(mentioned)
            exact = [p for p in changed_paths if p == mentioned or basename_key(p) == key]
            if len(exact) == 1:
                bulletin_mentions.setdefault(exact[0], []).append(item["line"])
            elif len(exact) > 1:
                ambiguous.append({"bulletin_line": item["line"], "candidates": exact})
            else:
                fuzzy = fuzzy_match(key, list(changed_basenames.keys()))
                if fuzzy:
                    bulletin_mentions.setdefault(changed_basenames[fuzzy], []).append(
                        item["line"] + "  [fuzzy match, verify manually]"
                    )
                else:
                    phantom_entries.append({"bulletin_line": item["line"], "mentioned_path": mentioned})

    documented = {p: changes[p] for p in bulletin_mentions}
    undocumented = {p: changes[p] for p in changed_paths if p not in bulletin_mentions}

    return {
        "documented_changes": [
            {"path": p, "change_type": changes[p], "bulletin_lines": bulletin_mentions[p]}
            for p in sorted(documented)
        ],
        "undocumented_changes": [
            {"path": p, "change_type": changes[p], "reason": "File changed but not mentioned anywhere in the bulletin."}
            for p in sorted(undocumented)
        ],
        "phantom_bulletin_entries": phantom_entries,
        "ambiguous_matches": ambiguous,
        "summary": {
            "total_files_changed": len(changed_paths),
            "documented": len(documented),
            "undocumented": len(undocumented),
            "phantom_entries": len(phantom_entries),
            "ambiguous": len(ambiguous),
        },
    }


# --------------------------------------------------------------------------
# 4. Report rendering
# --------------------------------------------------------------------------
def to_markdown(report):
    s = report["summary"]
    lines = [
        "# Release Bulletin Cross-Verification Report", "",
        f"- Files changed: **{s['total_files_changed']}**",
        f"- Documented: **{s['documented']}**",
        f"- Undocumented changes: **{s['undocumented']}**",
        f"- Phantom bulletin entries: **{s['phantom_entries']}**",
        f"- Ambiguous matches: **{s['ambiguous']}**", "",
    ]
    if report["undocumented_changes"]:
        lines += ["## Undocumented changes (in files, missing from bulletin)", ""]
        for e in report["undocumented_changes"]:
            lines.append(f"- `{e['path']}` ({e['change_type']}) — not mentioned in the bulletin")
        lines.append("")
    if report["phantom_bulletin_entries"]:
        lines += ["## Phantom bulletin entries (in bulletin, missing from files)", ""]
        for e in report["phantom_bulletin_entries"]:
            lines.append(f"- Bulletin says: \"{e['bulletin_line']}\" — mentions `{e['mentioned_path']}`, no such file change found")
        lines.append("")
    if report["ambiguous_matches"]:
        lines += ["## Ambiguous matches (needs human/Agent judgment)", ""]
        for e in report["ambiguous_matches"]:
            lines.append(f"- Bulletin says: \"{e['bulletin_line']}\" — matches multiple changed files: {', '.join(e['candidates'])}")
        lines.append("")
    if report["documented_changes"]:
        lines += ["## Documented changes (matched cleanly)", ""]
        for e in report["documented_changes"]:
            lines.append(f"- `{e['path']}` ({e['change_type']}) — \"{e['bulletin_lines'][0]}\"")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before-dir"); ap.add_argument("--after-dir")
    ap.add_argument("--repo"); ap.add_argument("--from-ref"); ap.add_argument("--to-ref")
    ap.add_argument("--bulletin", required=True, help="Path to the release bulletin PDF")
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--out-md", default="report.md")
    args = ap.parse_args()

    if args.before_dir and args.after_dir:
        print(f"Diffing {args.before_dir}  ->  {args.after_dir} (hash compare)...")
        changes = diff_snapshots(args.before_dir, args.after_dir)
    elif args.repo and args.from_ref and args.to_ref:
        print(f"Diffing {args.repo}  {args.from_ref}..{args.to_ref} (git)...")
        changes = diff_git(args.repo, args.from_ref, args.to_ref)
    else:
        ap.error("Provide either --before-dir/--after-dir or --repo/--from-ref/--to-ref")

    print(f"Found {len(changes)} changed files. Reading bulletin: {args.bulletin}")
    text = extract_pdf_text(args.bulletin)
    bulletin_items = extract_bulletin_items(text)
    print(f"Parsed {len(bulletin_items)} bulletin lines "
          f"({sum(1 for i in bulletin_items if i['paths'])} mention a filename-like token).")

    report = cross_verify(changes, bulletin_items)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(to_markdown(report))

    print(json.dumps(report["summary"], indent=2))
    print(f"\nFull report: {args.out} / {args.out_md}")


if __name__ == "__main__":
    main()
