#!/usr/bin/env python3
"""生成单页 nav 的 MkDocs 配置（INHERIT 主配置），用于只把一篇 Markdown 打进 print/PDF。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: 需要 PyYAML（requirements-docs.txt 随 mkdocs 已安装）", file=sys.stderr)
    sys.exit(1)


def normalize_md_rel(raw: str) -> str:
    s = raw.strip().replace("\\", "/").strip("/")
    if s.startswith("docs/"):
        s = s[len("docs/") :]
    if not s.endswith(".md"):
        s = f"{s}.md"
    return s


def first_h1_title(md_path: Path) -> str:
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: 无法读取 {md_path}: {exc}", file=sys.stderr)
        sys.exit(1)
    for line in text.splitlines():
        if line.startswith("# "):
            t = line[2:].strip()
            return (t[:200] if t else md_path.stem)
    return Path(md_path.name).stem


def main() -> int:
    ap = argparse.ArgumentParser(description="写出 INHERIT + 单条 nav 的 YAML。")
    ap.add_argument(
        "md_rel",
        help="相对 docs/ 的路径，如 esp32p4/note.md",
    )
    ap.add_argument(
        "-o",
        "--output",
        default="mkdocs.docflow.single.yml",
        help="输出文件（默认仓库根目录 mkdocs.docflow.single.yml）",
    )
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    md_rel = normalize_md_rel(args.md_rel)
    md_abs = root / "docs" / md_rel
    if not md_abs.is_file():
        print(f"error: 文件不存在: {md_abs}", file=sys.stderr)
        return 1
    title = first_h1_title(md_abs)
    out = Path(args.output)
    if not out.is_absolute():
        out = root / out
    doc = {"INHERIT": "mkdocs.yml", "nav": [{title: md_rel}]}
    out.write_text(
        yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
