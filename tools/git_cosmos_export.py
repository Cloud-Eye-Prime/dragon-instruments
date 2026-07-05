#!/usr/bin/env python3
"""git_cosmos_export.py -- turn a git repo's history into a Git Cosmos field.

Walks `git log` and emits a single history.json that public/git_cosmos.html
renders as a 3D flythrough: each commit is a star on a time-helix, lanes are
concentric rings (the branch structure), color is the author, size is churn,
and parent edges braid the DAG.

No dependencies beyond Python 3.8+ and the `git` CLI. Run inside any repo:

    python git_cosmos_export.py > history.json
    python git_cosmos_export.py --repo /path/to/repo --limit 1500 -o history.json

Then open public/git_cosmos.html and drop history.json onto it (or serve the
json beside the page and load it with ?data=history.json).

Design notes:
- Lanes come from the classic commit-graph column-packing pass (below), done
  here where the full parent DAG is in hand, so the browser only renders.
- Churn (insertions/deletions/files) is read from one `git log --numstat`
  pass, not N per-commit calls -- fast on large repos.
- Nothing is invented: a field that git does not provide is emitted empty or
  null, never guessed. The commit_url_template is derived from origin only for
  hosts whose commit path we actually know (GitHub/GitLab/Bitbucket).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

# ASCII field/record separators -- safe inside commit messages, unlike commas.
US = "\x1f"  # unit separator between fields
RS = "\x1e"  # record separator between commits

_PRETTY = US.join(["%H", "%P", "%an", "%ae", "%at", "%s", "%D"]) + RS


def _git(args: List[str], cwd: str) -> str:
    """Run a git command, returning stdout. Raises on non-zero exit so the
    caller can fail honestly rather than emit a half-built field."""
    proc = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "git %s failed: %s" % (" ".join(args), proc.stderr.strip()))
    return proc.stdout


def _read_commits(cwd: str, limit: int, all_refs: bool) -> List[Dict]:
    """Parse the log into commit dicts (no lane, no churn yet)."""
    args = ["log", "--date-order", "--pretty=format:" + _PRETTY]
    if all_refs:
        args.insert(1, "--all")
    if limit > 0:
        args.insert(1, "--max-count=%d" % limit)
    raw = _git(args, cwd)
    commits: List[Dict] = []
    for rec in raw.split(RS):
        rec = rec.strip("\n")
        if not rec:
            continue
        parts = rec.split(US)
        if len(parts) < 7:
            continue
        sha, parents, an, ae, at, subject, decor = parts[:7]
        try:
            ts = int(at)
        except ValueError:
            ts = 0
        refs = [r.strip() for r in decor.split(",") if r.strip()] if decor else []
        commits.append({
            "sha": sha,
            "short": sha[:9],
            "parents": [p for p in parents.split(" ") if p],
            "author": an,
            "email": ae,
            "ts": ts,
            "subject": subject,
            "refs": refs,
            "insertions": 0,
            "deletions": 0,
            "files": 0,
            "lane": 0,
        })
    return commits


def _read_churn(cwd: str, limit: int, all_refs: bool) -> Dict[str, Tuple[int, int, int]]:
    """One numstat pass -> {sha: (insertions, deletions, files)}.

    numstat prints, per commit, a header line we mark with our sha, then one
    '<ins>\\t<del>\\t<path>' line per file. Binary files report '-' for the
    counts; those add to the file count but not the line totals.
    """
    args = ["log", "--numstat", "--pretty=format:" + RS + "%H", "--no-renames"]
    if all_refs:
        args.insert(1, "--all")
    if limit > 0:
        args.insert(1, "--max-count=%d" % limit)
    raw = _git(args, cwd)
    out: Dict[str, Tuple[int, int, int]] = {}
    cur: Optional[str] = None
    ins = dels = files = 0
    for line in raw.split("\n"):
        if line.startswith(RS):
            if cur is not None:
                out[cur] = (ins, dels, files)
            cur = line[1:].strip()
            ins = dels = files = 0
            continue
        if not line.strip() or cur is None:
            continue
        cols = line.split("\t")
        if len(cols) < 3:
            continue
        a, d = cols[0], cols[1]
        files += 1
        if a.isdigit():
            ins += int(a)
        if d.isdigit():
            dels += int(d)
    if cur is not None:
        out[cur] = (ins, dels, files)
    return out


def _assign_lanes(commits: List[Dict]) -> None:
    """Classic commit-graph column packing, in git log order (a commit is
    emitted before its parents). Each column 'awaits' the next sha it expects;
    a commit takes the column awaiting it (or a free one), then that column
    starts awaiting its first parent, while extra (merge) parents open columns.
    Duplicate awaits collapse to the leftmost, keeping lane numbers small and
    stable. Sets commit['lane'] in place."""
    active: List[Optional[str]] = []

    def reserve(sha: str) -> int:
        for i, a in enumerate(active):
            if a == sha:
                return i
        for i, a in enumerate(active):
            if a is None:
                active[i] = sha
                return i
        active.append(sha)
        return len(active) - 1

    for c in commits:
        col = reserve(c["sha"])
        c["lane"] = col
        parents = c["parents"]
        active[col] = parents[0] if parents else None
        for p in parents[1:]:
            reserve(p)
        # collapse: multiple columns awaiting the same sha -> keep the leftmost
        seen = set()
        for i, a in enumerate(active):
            if a is None:
                continue
            if a in seen:
                active[i] = None
            else:
                seen.add(a)


def _commit_url_template(cwd: str) -> Optional[str]:
    """Derive an https commit-URL template from origin, for hosts whose commit
    path we actually know. Returns None (never a guess) otherwise."""
    try:
        url = _git(["remote", "get-url", "origin"], cwd).strip()
    except RuntimeError:
        return None
    if not url:
        return None
    m = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", url)
    if m:
        host, path = m.group(1), m.group(2)
    else:
        m = re.match(r"https?://(?:[^@/]+@)?([^/]+)/(.+?)(?:\.git)?$", url)
        if not m:
            return None
        host, path = m.group(1), m.group(2)
    host = host.lower()
    if "github" in host or "gitlab" in host:
        return "https://%s/%s/commit/{sha}" % (host, path)
    if "bitbucket" in host:
        return "https://%s/%s/commits/{sha}" % (host, path)
    return None


def _current(cwd: str, what: str) -> str:
    try:
        return _git(what.split(), cwd).strip()
    except RuntimeError:
        return ""


def build(cwd: str, limit: int, all_refs: bool,
          generated_utc: str = "") -> Dict:
    """Assemble the full history document for one repo."""
    commits = _read_commits(cwd, limit, all_refs)
    if not commits:
        raise RuntimeError("no commits found (is this a git repo with history?)")
    churn = _read_churn(cwd, limit, all_refs)
    for c in commits:
        ins, dels, files = churn.get(c["sha"], (0, 0, 0))
        c["insertions"], c["deletions"], c["files"] = ins, dels, files
    _assign_lanes(commits)
    head = _current(cwd, "rev-parse HEAD")
    branch = _current(cwd, "rev-parse --abbrev-ref HEAD")
    repo = _current(cwd, "rev-parse --show-toplevel").replace("\\", "/").rsplit("/", 1)[-1]
    return {
        "repo": repo or "repo",
        "generated_utc": generated_utc,
        "head": head,
        "branch": branch,
        "commit_url_template": _commit_url_template(cwd),
        "lanes": (max(c["lane"] for c in commits) + 1) if commits else 0,
        "count": len(commits),
        "commits": commits,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Export git history for Git Cosmos.")
    ap.add_argument("--repo", default=".", help="path to the repo (default: cwd)")
    ap.add_argument("--limit", type=int, default=2000,
                    help="max commits (0 = all; default 2000, browser-friendly)")
    ap.add_argument("--all", action="store_true",
                    help="include all refs/branches, not just HEAD's history")
    ap.add_argument("-o", "--out", default="-",
                    help="output file (default: - = stdout)")
    ap.add_argument("--generated-utc", default="",
                    help="optional ISO timestamp to stamp into the file")
    args = ap.parse_args(argv)
    try:
        doc = build(args.repo, args.limit, args.all, args.generated_utc)
    except (RuntimeError, FileNotFoundError) as e:
        sys.stderr.write("git_cosmos_export: %s\n" % e)
        return 1
    text = json.dumps(doc, ensure_ascii=True, separators=(",", ":"))
    if args.out == "-":
        sys.stdout.write(text + "\n")
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write("wrote %s (%d commits, %d lanes)\n"
                         % (args.out, doc["count"], doc["lanes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
