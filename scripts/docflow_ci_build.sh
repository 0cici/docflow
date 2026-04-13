#!/usr/bin/env bash
# CI：为变更的 docs/**/*.md 各生成一份 PDF（文件名 = 该 .md 的文件名 stem），再全量 mkdocs build，将 PDF 拷入 site/pdf/。
# 用法: docflow_ci_build.sh <git_base_sha> [git_head_sha]
#   git_base_sha 为全 0 或空时，视为「列出仓库内全部已跟踪的 docs 下 .md」（仅用于首推送等场景）。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BASE="${1:-}"
HEAD="${2:-HEAD}"
PY="${PYTHON:-python3}"
STASH="$(mktemp -d)"
cleanup() {
  rm -rf "$STASH"
  rm -f "$ROOT/mkdocs.docflow.single.yml"
}
trap cleanup EXIT

while IFS= read -r md; do
  [[ -z "$md" ]] && continue
  "$PY" scripts/write_mkdocs_single_nav.py "$md" -o "$ROOT/mkdocs.docflow.single.yml"
  T="$(mktemp -d)"
  mkdocs build -f "$ROOT/mkdocs.docflow.single.yml" -d "$T/site" --strict
  export DOCFLOW_SITE_DIR="$T/site"
  export DOCFLOW_PDF_NAME="$(basename "$md" .md).pdf"
  "$PY" scripts/render_pdf.py
  cp "$T/site/pdf/$DOCFLOW_PDF_NAME" "$STASH/"
  unset DOCFLOW_SITE_DIR DOCFLOW_PDF_NAME
  rm -rf "$T"
done < <("$PY" scripts/list_changed_docs_md.py --base "$BASE" --head "$HEAD")

# 全量构建会清空 site/；若本地已有 site/pdf（或需保留未在本次 diff 中的 PDF），先备份再合并。
PDF_BACKUP="$(mktemp -d)"
if [[ -d site/pdf ]]; then
  shopt -s nullglob
  for f in site/pdf/*.pdf; do
    cp "$f" "$PDF_BACKUP/"
  done
  shopt -u nullglob
fi

mkdocs build --strict
mkdir -p site/pdf
shopt -s nullglob
for f in "$STASH"/*.pdf; do
  cp "$f" site/pdf/
done
for f in "$PDF_BACKUP"/*.pdf; do
  [[ -e "$f" ]] || continue
  b=$(basename "$f")
  [[ -e "site/pdf/$b" ]] || cp "$f" "site/pdf/$b"
done
shopt -u nullglob
rm -rf "$PDF_BACKUP"
ls -la site/pdf/ 2>/dev/null || true
