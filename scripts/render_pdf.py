#!/usr/bin/env python3
"""将 print_page 打成 PDF：修正 /static/ 路径、注入 weasyprint-pdf.css、可选页眉图与全页对角线底纹、动态页脚。"""

from __future__ import annotations

import calendar
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from html import escape
from pathlib import Path

# macOS：dyld 只在进程启动时读取 DYLD_FALLBACK_LIBRARY_PATH；在脚本里 import 前改 os.environ 无效。
# 若检测到 Homebrew 的 libpango，则用正确库路径重新 exec 当前解释器（仅一次）。
_DYLD_FLAG = "DOCFLOW_WEASYPRINT_DYLD_DONE"


def _homebrew_lib_dirs_with_pango() -> list[str]:
    """常见前缀 + brew --prefix，避免 Homebrew 装在非标准路径。"""
    dirs: list[str] = []
    for prefix in ("/opt/homebrew", "/usr/local"):
        lib = Path(prefix) / "lib"
        if (lib / "libpango-1.0.dylib").is_file() and str(lib) not in dirs:
            dirs.append(str(lib))

    brew = shutil.which("brew")
    if brew:
        try:
            proc = subprocess.run(
                [brew, "--prefix"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            if proc.returncode == 0:
                lib = Path(proc.stdout.strip()) / "lib"
                if (lib / "libpango-1.0.dylib").is_file():
                    s = str(lib.resolve())
                    if s not in dirs:
                        dirs.append(s)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return dirs


def _maybe_reexec_with_homebrew_dyld() -> None:
    if sys.platform != "darwin":
        return
    if os.environ.get(_DYLD_FLAG) == "1":
        return

    lib_dirs = _homebrew_lib_dirs_with_pango()
    if not lib_dirs:
        return

    sep = os.pathsep
    extra = sep.join(lib_dirs)
    prev = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    merged = extra if not prev else f"{extra}{sep}{prev}"

    env = os.environ.copy()
    env["DYLD_FALLBACK_LIBRARY_PATH"] = merged
    env[_DYLD_FLAG] = "1"

    script = Path(__file__).resolve()
    argv = [sys.executable, str(script), *sys.argv[1:]]
    os.execve(sys.executable, argv, env)


def _brew_prefix_path() -> Path | None:
    brew = shutil.which("brew")
    if not brew:
        return None
    try:
        proc = subprocess.run(
            [brew, "--prefix"], capture_output=True, text=True, timeout=8, check=False
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return Path(proc.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        return None


def _darwin_arm64_intel_homebrew() -> bool:
    """Apple Silicon 上使用默认的 /usr/local brew（多为 x86_64 库）。"""
    if sys.platform != "darwin" or platform.machine() != "arm64":
        return False
    pref = _brew_prefix_path()
    return pref is not None and pref == Path("/usr/local")


def _darwin_arch_mismatch_hint() -> str:
    return (
        "检测到本机 Python 为 arm64，但 brew --prefix 为 /usr/local（多为 Rosetta/Intel Homebrew）。\n"
        "/usr/local/lib 里的 Pango 通常是 x86_64，WeasyPrint 无法用 arm64 Python 加载（表现成找不到 libpango 或 incompatible architecture）。\n\n"
        "任选其一：\n"
        "  A) 使用 Apple Silicon 版 Homebrew（/opt/homebrew），安装 arm64 依赖并用其 Python：\n"
        "       /opt/homebrew/bin/brew install pango gdk-pixbuf cairo\n"
        "       rm -rf .venv && /opt/homebrew/bin/python3 -m venv .venv\n"
        "       .venv/bin/pip install -r requirements-docs.txt\n\n"
        "  B) 继续用 /usr/local 的 Pango，改用 x86_64 Python 建 venv：\n"
        "       rm -rf .venv && arch -x86_64 /usr/local/bin/python3 -m venv .venv\n"
        "       .venv/bin/pip install -r requirements-docs.txt\n"
        "     （若 python3 不在该路径，可先 which -a python3 选用 Intel 前缀下的解释器。）\n"
    )


def _watermark_image_src(root: Path) -> tuple[Path | None, str | None]:
    """若存在水印文件则返回 (path, img 元素的 src 属性值)；否则 (None, None)。"""
    env_wm = os.environ.get("DOCFLOW_PDF_WATERMARK")
    wm = Path(env_wm).expanduser() if env_wm else root / "docs" / "static" / "espressif-standard-logo.png"
    if not wm.is_file():
        if env_wm:
            print(f"warning: DOCFLOW_PDF_WATERMARK 文件不存在: {wm}", file=sys.stderr)
        return None, None
    return wm, wm.resolve().as_uri()


def _revision_date_footer_label(now: datetime | None = None) -> str:
    """页脚右侧「修订日期」，默认英文缩写月 + 年（如 Apr. 2026），按本机编译时刻生成。

    可设置环境变量 DOCFLOW_PDF_REVISION_DATE 覆盖（例如 CI 固定复现）。
    """
    env = os.environ.get("DOCFLOW_PDF_REVISION_DATE", "").strip()
    if env:
        return env
    dt = now or datetime.now()
    return f"{calendar.month_abbr[dt.month]}. {dt.year}"


def _pdf_footer_stylesheet(revision_date_right: str):
    """页脚居中：当前页/总页数；页脚居右：修订日期。覆盖 HTML 内 print-site-material 的 @page 页脚。"""
    from weasyprint import CSS

    safe = revision_date_right.replace("\\", "\\\\").replace('"', '\\"')
    font = (
        '"Helvetica Neue", "HelveticaNeue", "Nimbus Sans", '
        '"Nimbus Sans L", Helvetica, Arial, "Liberation Sans", sans-serif'
    )
    # content 必须 !important：否则 HTML 内 print-site-material.css（作者样式）的 @page 页脚会覆盖 user 样式表
    return CSS(
        string=f"""
    @page {{
      @bottom-left {{
        content: none !important;
      }}
      @bottom-center {{
        content: counter(page) " / " counter(pages) !important;
        font-size: 9pt;
        color: #333333;
        font-family: {font};
        vertical-align: top;
      }}
      @bottom-right {{
        content: "{safe}" !important;
        font-size: 9pt;
        color: #333333;
        font-family: {font};
        vertical-align: top;
        text-align: right;
      }}
    }}
    """
    )


def _diagonal_watermark_text() -> str | None:
    """全页对角线底纹文案。未设置环境变量时默认 ESPRESSIF CONFIDENTIAL；设为 0/false/off 或空串则关闭。

    覆盖：DOCFLOW_PDF_DIAGONAL_WATERMARK=自定义文案
    """
    raw = os.environ.get("DOCFLOW_PDF_DIAGONAL_WATERMARK")
    if raw is not None:
        s = raw.strip()
        if s == "" or s.lower() in ("0", "false", "off", "no", "none"):
            return None
        return s
    return "ESPRESSIF CONFIDENTIAL"


_MARGIN_HEADER_BLOCK_RE = re.compile(
    r'(<div\s+class="docflow-pdf-margin-header"[^>]*>)\s*<img\b[^>]*>',
    re.IGNORECASE | re.DOTALL,
)


def _sync_margin_header_image(html: str, wm_src: str) -> str:
    """已注入页眉块时，更新其中 <img src>（换默认 logo 文件名后无需删 site）。"""
    esc = escape(wm_src, quote=True)
    return _MARGIN_HEADER_BLOCK_RE.sub(
        rf'\1<img src="{esc}" alt="" />',
        html,
        count=1,
    )


def _inject_pdf_body_overlays(
    html: str, *, diagonal_text: str | None, wm_src: str | None
) -> str:
    """在 <body> 起始处注入：对角线底纹（先，衬底）、页眉 logo（后）。已存在对应 class 则跳过注入；页眉已存在则仅同步 logo 的 src。"""
    out = html
    if wm_src and "docflow-pdf-margin-header" in out:
        out = _sync_margin_header_image(out, wm_src)

    parts: list[str] = []
    if diagonal_text and "docflow-pdf-diagonal-watermark" not in out:
        parts.append(
            '<div class="docflow-pdf-diagonal-watermark" aria-hidden="true">'
            f"<span>{escape(diagonal_text)}</span></div>"
        )
    if wm_src and "docflow-pdf-margin-header" not in out:
        parts.append(
            '<div class="docflow-pdf-margin-header" aria-hidden="true">'
            f'<img src="{escape(wm_src, quote=True)}" alt="" /></div>'
        )
    if not parts:
        return out
    return re.sub(
        r"(<body[^>]*>)",
        r"\1" + "".join(parts),
        out,
        count=1,
        flags=re.IGNORECASE,
    )


def _darwin_pango_hint() -> str:
    return (
        "未在常见路径找到 libpango-1.0.dylib（已尝试 /opt/homebrew、/usr/local 以及 brew --prefix）。\n"
        "请在本机任意目录执行: brew install pango gdk-pixbuf cairo\n"
        "装好后自检: ls \"$(brew --prefix)/lib\"/libpango*.dylib\n"
        "Apple Silicon 请用 arm64 的 /opt/homebrew/bin/brew；勿混用 arm64 Python 与仅装在 /usr/local 的 x86 库。"
    )


_MKDOCS_YAML_ENV_REGISTERED = False


def _register_mkdocs_yaml_env_tag() -> None:
    """MkDocs 使用 !ENV 标签；标准 PyYAML 需注册后才能解析 nav。"""
    global _MKDOCS_YAML_ENV_REGISTERED
    if _MKDOCS_YAML_ENV_REGISTERED:
        return
    try:
        import yaml
    except ImportError:
        return

    def _env_tag(loader: object, node: object) -> object:
        if isinstance(node, yaml.SequenceNode):
            seq = loader.construct_sequence(node)  # type: ignore[union-attr]
            if len(seq) > 1:
                return seq[1]
            return seq[0] if seq else ""
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)  # type: ignore[union-attr]
        return None

    yaml.add_constructor("!ENV", _env_tag, Loader=yaml.SafeLoader)
    _MKDOCS_YAML_ENV_REGISTERED = True


def _nav_markdown_paths(nav: object, out: list[str]) -> None:
    """按 mkdocs nav 顺序深度优先收集 .md 路径字符串。"""
    if nav is None:
        return
    if isinstance(nav, list):
        for item in nav:
            _nav_markdown_paths(item, out)
    elif isinstance(nav, dict):
        for v in nav.values():
            if isinstance(v, str) and v.endswith(".md"):
                out.append(v)
            else:
                _nav_markdown_paths(v, out)


def _pdf_basename_from_mkdocs(root: Path) -> str:
    yml = root / "mkdocs.yml"
    if not yml.is_file():
        return "docflow.pdf"
    try:
        import yaml
    except ImportError:
        return "docflow.pdf"
    _register_mkdocs_yaml_env_tag()
    try:
        data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
    except Exception:
        return "docflow.pdf"
    paths: list[str] = []
    _nav_markdown_paths(data.get("nav"), paths)
    if not paths:
        return "docflow.pdf"
    stem = Path(Path(paths[0]).name).stem
    if not stem.strip():
        return "docflow.pdf"
    return f"{stem}.pdf"


def pdf_basename_for_output(root: Path) -> str:
    """输出 PDF 文件名：DOCFLOW_PDF_NAME > DOCFLOW_SOURCE_MD > mkdocs nav 首条 .md。"""
    env = os.environ.get("DOCFLOW_PDF_NAME", "").strip()
    if env:
        name = Path(env).name
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf"
        return name
    src = os.environ.get("DOCFLOW_SOURCE_MD", "").strip()
    if src:
        s = src.replace("\\", "/").lstrip("/")
        if s.startswith("docs/"):
            s = s[len("docs/") :]
        stem = Path(s).name
        if stem.endswith(".md"):
            stem = Path(stem).stem
        if stem.strip():
            return f"{stem}.pdf"
    return _pdf_basename_from_mkdocs(root)


def site_output_dir(root: Path) -> Path:
    """WeasyPrint 使用的站点输出目录，默认 site；可由 DOCFLOW_SITE_DIR 覆盖（绝对或相对仓库根）。"""
    raw = (os.environ.get("DOCFLOW_SITE_DIR") or "site").strip() or "site"
    p = Path(raw).expanduser()
    return p.resolve() if p.is_absolute() else (root / p).resolve()


def default_pdf_path(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parent.parent
    return site_output_dir(root) / "pdf" / pdf_basename_for_output(root)


def main() -> int:
    _maybe_reexec_with_homebrew_dyld()

    root = Path(__file__).resolve().parent.parent
    site_dir = site_output_dir(root)
    html_path = site_dir / "print_page" / "index.html"
    css_path = root / "docs" / "css" / "weasyprint-pdf.css"
    pdf_path = default_pdf_path(root)

    if not html_path.is_file():
        print(f"error: missing {html_path}", file=sys.stderr)
        return 1

    try:
        from weasyprint import CSS, HTML
    except OSError as exc:
        print(f"error: WeasyPrint or system libraries: {exc}", file=sys.stderr)
        if sys.platform == "darwin":
            msg_l = str(exc).lower()
            if _darwin_arm64_intel_homebrew() or "incompatible architecture" in msg_l:
                print(_darwin_arch_mismatch_hint(), file=sys.stderr)
            else:
                print(_darwin_pango_hint(), file=sys.stderr)
        return 1

    text0 = html_path.read_text(encoding="utf-8")
    fixed = text0.replace('src="/static/', 'src="../static/')
    _, wm_src = _watermark_image_src(root)
    fixed = _inject_pdf_body_overlays(
        fixed,
        diagonal_text=_diagonal_watermark_text(),
        wm_src=wm_src,
    )
    if fixed != text0:
        html_path.write_text(fixed, encoding="utf-8")

    doc = HTML(filename=str(html_path))
    sheets: list = []
    if css_path.is_file():
        sheets.append(CSS(filename=str(css_path)))
    sheets.append(_pdf_footer_stylesheet(_revision_date_footer_label()))

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.write_pdf(str(pdf_path), stylesheets=sheets)
    print(f"wrote {pdf_path} (footer date: {_revision_date_footer_label()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
