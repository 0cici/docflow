#!/usr/bin/env python3
"""列出两次 git 提交之间变更的 docs 下 .md（相对 docs/）。无有效 base 时列出所有已跟踪的 docs/**/*.md。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run_git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        sys.exit(proc.returncode or 1)
    return proc.stdout


def _is_all_zero_sha(s: str) -> bool:
    s = s.strip()
    return not s or set(s) == {"0"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="", help="git diff 起始提交（如 push 的 before）")
    ap.add_argument("--head", default="HEAD", help="git diff 结束提交，默认 HEAD")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    docs = root / "docs"
    if not docs.is_dir():
        return 0

    base = (args.base or "").strip()
    head = (args.head or "HEAD").strip()

    paths: list[str] = []
    if _is_all_zero_sha(base):
        out = _run_git(["ls-files", "-z", "--", "docs"], cwd=root)
        for raw in out.split("\0"):
            if not raw or not raw.endswith(".md"):
                continue
            rel = Path(raw).as_posix()
            if not rel.startswith("docs/"):
                continue
            rel_to_docs = rel[len("docs/") :]
            if rel_to_docs:
                paths.append(rel_to_docs)
    else:
        out = _run_git(["diff", "--name-only", f"{base}..{head}"], cwd=root)
        for line in out.splitlines():
            line = line.strip().replace("\\", "/")
            if not line.startswith("docs/") or not line.endswith(".md"):
                continue
            rel_to_docs = line[len("docs/") :]
            if rel_to_docs and (docs / rel_to_docs).is_file():
                paths.append(rel_to_docs)

    for p in sorted(set(paths)):
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
