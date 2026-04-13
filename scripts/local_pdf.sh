#!/usr/bin/env bash
# 本地：必须指定要出 PDF 的 Markdown（相对 docs/ 的路径），再全量 mkdocs build。
# 用法: ./scripts/local_pdf.sh esp32p4/esp32p4-chip-revision-v3.1-sample-notes_en.md
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <docs 下相对路径，如 esp32p4/xxx.md>" >&2
  exit 1
fi
MD_REL_RAW="$1"

if [[ "$(uname -m)" == arm64 ]] && command -v brew >/dev/null 2>&1 && [[ "$(brew --prefix)" == "/usr/local" ]]; then
  echo "" >&2
  echo "docflow: 当前是 arm64 Mac，但 brew --prefix 为 /usr/local（多为 Intel 版 Homebrew/Pango）。" >&2
  echo "若 WeasyPrint 报错，请改用 /opt/homebrew 的 Python 与 pango，或 arch -x86_64 … -m venv .venv。README 有步骤。" >&2
  echo "" >&2
fi

if command -v brew >/dev/null 2>&1; then
  _BREW_PREF="$(brew --prefix)"
  export DYLD_FALLBACK_LIBRARY_PATH="${_BREW_PREF}/lib:/opt/homebrew/lib:/usr/local/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
  export PKG_CONFIG_PATH="${_BREW_PREF}/lib/pkgconfig:/opt/homebrew/lib/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
else
  export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:/usr/local/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
  export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
fi

PY="${ROOT}/.venv/bin/python"
PIP="${ROOT}/.venv/bin/pip"
MKDOCS="${ROOT}/.venv/bin/mkdocs"

if [[ ! -x "$PY" ]]; then
  python3 -m venv .venv
fi

"$PIP" install -q -r requirements-docs.txt

: "${MKDOCS_SITE_URL:=http://127.0.0.1:8000/}"
: "${MKDOCS_REPO_URL:=https://github.com/example/docflow}"
export MKDOCS_SITE_URL MKDOCS_REPO_URL

SINGLE_YML="${ROOT}/mkdocs.docflow.single.yml"
TMP_ROOT="$(mktemp -d)"
TMP_SITE="${TMP_ROOT}/site"
cleanup() {
  rm -f "$SINGLE_YML"
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

"$PY" scripts/write_mkdocs_single_nav.py "$MD_REL_RAW" -o "$SINGLE_YML"
"$MKDOCS" build -f "$SINGLE_YML" -d "$TMP_SITE" --strict
export DOCFLOW_SITE_DIR="$TMP_SITE"
_r="${MD_REL_RAW#./}"
_r="${_r#docs/}"
[[ "$_r" == *.md ]] || _r="${_r}.md"
STEM="${_r##*/}"
STEM="${STEM%.md}"
export DOCFLOW_PDF_NAME="${STEM}.pdf"
"$PY" scripts/render_pdf.py
unset DOCFLOW_SITE_DIR DOCFLOW_PDF_NAME

"$MKDOCS" build --strict
mkdir -p "${ROOT}/site/pdf"
cp "${TMP_SITE}/pdf/${STEM}.pdf" "${ROOT}/site/pdf/"
echo "PDF: ${ROOT}/site/pdf/${STEM}.pdf"
