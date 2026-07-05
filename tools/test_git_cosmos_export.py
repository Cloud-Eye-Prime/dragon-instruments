"""Tests for git_cosmos_export -- built against a real temp git repo.

Covers the JSON contract the browser depends on (schema, parents = the DAG),
the lane-packing pass on a branch+merge topology, churn aggregation, and the
honest-empty behavior (no invented fields).

Run: python -m pytest tools/test_git_cosmos_export.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import git_cosmos_export as gce


def _run(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, name: str, text: str) -> None:
    (repo / name).write_text(text + "\n", encoding="utf-8")
    _run(repo, "add", name)
    _run(repo, "commit", "-q", "-m", "add " + name)


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    _run(r, "init", "-q", "-b", "main")
    _run(r, "config", "user.email", "t@t")
    _run(r, "config", "user.name", "Tester")
    _commit(r, "a.txt", "one\ntwo\nthree")   # root
    _commit(r, "b.txt", "x")                 # linear
    _run(r, "checkout", "-q", "-b", "feature")
    _commit(r, "c.txt", "feature work")      # on feature
    _run(r, "checkout", "-q", "main")
    _commit(r, "d.txt", "main work")         # diverged on main
    _run(r, "merge", "-q", "--no-ff", "feature", "-m", "merge feature")
    return r


# --- schema / DAG ----------------------------------------------------------

def test_document_shape(repo):
    doc = gce.build(str(repo), limit=0, all_refs=True)
    for key in ("repo", "head", "branch", "count", "lanes", "commits"):
        assert key in doc
    assert doc["count"] == len(doc["commits"]) == 5  # a,b,c,d + merge
    c0 = doc["commits"][0]
    for key in ("sha", "short", "parents", "author", "ts", "subject",
                "insertions", "deletions", "files", "lane", "refs"):
        assert key in c0


def test_parents_form_the_dag(repo):
    doc = gce.build(str(repo), limit=0, all_refs=True)
    by_sha = {c["sha"]: c for c in doc["commits"]}
    merges = [c for c in doc["commits"] if len(c["parents"]) == 2]
    assert len(merges) == 1  # exactly one merge commit
    # both parents of the merge are real commits in the set
    for p in merges[0]["parents"]:
        assert p in by_sha
    roots = [c for c in doc["commits"] if not c["parents"]]
    assert len(roots) == 1  # single root


def test_head_and_author(repo):
    doc = gce.build(str(repo), limit=0, all_refs=True)
    assert len(doc["head"]) == 40
    assert doc["branch"] == "main"
    assert all(c["author"] == "Tester" for c in doc["commits"])


# --- lanes -----------------------------------------------------------------

def test_lane_packing_uses_multiple_lanes_and_is_small(repo):
    doc = gce.build(str(repo), limit=0, all_refs=True)
    lanes = {c["lane"] for c in doc["commits"]}
    # a branch+merge topology must use at least 2 lanes...
    assert len(lanes) >= 2
    # ...but packing keeps lane numbers small and contiguous from 0
    assert min(lanes) == 0
    assert max(lanes) == doc["lanes"] - 1
    assert max(lanes) < 5  # no lane explosion on a tiny graph


# --- churn -----------------------------------------------------------------

def test_churn_counted(repo):
    doc = gce.build(str(repo), limit=0, all_refs=True)
    root = next(c for c in doc["commits"] if not c["parents"])
    # the root added a.txt with three lines
    assert root["insertions"] == 3
    assert root["files"] == 1
    assert root["deletions"] == 0


# --- honesty ---------------------------------------------------------------

def test_no_remote_yields_null_template_not_a_guess(repo):
    doc = gce.build(str(repo), limit=0, all_refs=True)
    assert doc["commit_url_template"] is None  # no origin -> honest null


def test_github_remote_template(repo):
    _run(repo, "remote", "add", "origin",
         "git@github.com:Owner/my-repo.git")
    doc = gce.build(str(repo), limit=0, all_refs=True)
    assert doc["commit_url_template"] == \
        "https://github.com/Owner/my-repo/commit/{sha}"


def test_limit_caps_commit_count(repo):
    doc = gce.build(str(repo), limit=2, all_refs=False)
    assert doc["count"] <= 2


def test_output_is_pure_ascii(repo):
    doc = gce.build(str(repo), limit=0, all_refs=True)
    text = json.dumps(doc, ensure_ascii=True)
    text.encode("ascii")  # raises if any non-ascii slipped in
