# docflow

Pilot project for one-off documents.

## CI（`.github/workflows/pre_commit.yml`）

向 **`main` 或 `master`**（PR 的**目标分支**）开 PR，或推送到这两条分支时，会依次执行：

1. **Pre-commit**：运行 `.pre-commit-config.yaml`（含 **codespell**）。
2. **Build**：安装 WeasyPrint 系统依赖后运行 **`bash scripts/docflow_ci_build.sh`**（由 workflow 传入 git 基线与 HEAD）。脚本会对比 **本次 PR 或本次 push** 相对基线的差异，对每一个变更的 **`docs/**/*.md`** 单独用 **`INHERIT` + 单页 `nav`** 做一次 `mkdocs build`，再 **`python3 scripts/render_pdf.py`** 生成 **`site/pdf/<该文件名的 stem>.pdf`**（例如 `esp32p4/note_en.md` → `note_en.pdf`）；最后再用主 **`mkdocs.yml`** 全量构建站点并把上述 PDF 拷入最终 **`site/pdf/`**。若本次提交**没有**改动任何 `docs` 下的 `.md`，则不会新增 PDF，全量站点仍会生成（此时 artifact 里 **`pdf/`** 可能为空）。**首次推送**等无有效 `before` 提交时，脚本会对仓库内**全部**已跟踪的 `docs/**/*.md` 各生成一份 PDF（与「列出全部变更」逻辑一致）。
3. **PR 评论**：对**同仓库**内发起的 PR（非 fork），Build 成功后会自动发/更新一条评论，内含**本次 workflow 运行**链接；在运行页底部 **Artifacts** 下载 **site**。GitHub 不提供 artifact 的公开直链，因此评论里是「运行页链接」而不是 zip 直链。**来自 fork 的 PR** 默认不会发评论（`GITHUB_TOKEN` 无写 PR 权限），但仍可在本仓库 **Actions** 里找到对应运行并下载 artifact。
4. **Deploy**：仅在 **push 到 `main` 或 `master`** 时，将 `site` 部署到 **GitHub Pages**（HTML 与 PDF 一并发布）。

提交前建议在本地安装钩子并自检：

```bash
pip install pre-commit
pre-commit install          # 每次 git commit 前运行钩子
pre-commit run --all-files  # 或手动跑一遍（与 CI 的 pre-commit job 一致）
```

本地生成 PDF（**必须指定**要导出的一篇 Markdown，路径相对于 **`docs/`**，可写 `esp32p4/xxx.md` 或 `docs/esp32p4/xxx.md`）：

1. 安装 **WeasyPrint 系统依赖**（[官方说明](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)）。**macOS（Apple Silicon）** 请用 **arm64 的 Homebrew** 安装，使库在 `/opt/homebrew/lib`（例如 `brew install pango gdk-pixbuf libffi cairo`）。若 Python 是 arm64 而 Pango 只有 Intel 版（`/usr/local`），会出现无法加载 `libpango` 或 **mach-o wrong architecture**。
2. 在项目根目录执行：

```bash
./scripts/local_pdf.sh esp32p4/esp32p4-chip-revision-v3.1-sample-notes_en.md
```

脚本会：生成临时的 **`mkdocs.docflow.single.yml`**（已加入 `.gitignore`）→ 单页构建 → **`render_pdf.py`** 写出 **`site/pdf/<该 .md 文件名的 stem>.pdf`** → 再执行主配置 **`mkdocs build --strict`** 得到完整站点。

等价手动步骤（**必须用虚拟环境里的命令**）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-docs.txt
export MKDOCS_SITE_URL=http://127.0.0.1:8000/
export MKDOCS_REPO_URL=https://github.com/<你的用户名>/<仓库名>
.venv/bin/python scripts/write_mkdocs_single_nav.py esp32p4/your-note.md -o mkdocs.docflow.single.yml
.venv/bin/mkdocs build -f mkdocs.docflow.single.yml -d /tmp/docflow-site --strict
export DOCFLOW_SITE_DIR=/tmp/docflow-site
export DOCFLOW_PDF_NAME=your-note.pdf   # 或与源文件 stem 一致
.venv/bin/python scripts/render_pdf.py
unset DOCFLOW_SITE_DIR DOCFLOW_PDF_NAME
.venv/bin/mkdocs build --strict
mkdir -p site/pdf && cp /tmp/docflow-site/pdf/your-note.pdf site/pdf/
```

环境变量 **`DOCFLOW_SITE_DIR`**：WeasyPrint 读取的站点目录（默认 **`site`**）。**`DOCFLOW_PDF_NAME`** / **`DOCFLOW_SOURCE_MD`**：控制输出 PDF 文件名（见 **`scripts/render_pdf.py`**）。

在 **macOS** 上，`scripts/render_pdf.py` 会在发现 Homebrew 的 `libpango-1.0.dylib` 时自动带上 **`DYLD_FALLBACK_LIBRARY_PATH`** 并**重新启动**解释器（否则仅改环境变量无法让 WeasyPrint 找到 Pango）。仍需先 **`brew install pango gdk-pixbuf cairo`**。

**Apple Silicon 常见坑：`brew --prefix` 为 `/usr/local`**

若 `which python3` 指向 **`/opt/homebrew/bin/python3`（arm64）**，而 **`brew --prefix` 为 `/usr/local`**，则 Pango 在 `/usr/local/lib` 里多为 **x86_64**，与 arm64 Python **不能混用**，会表现为找不到 `libpango` 或 `incompatible architecture`。

- **推荐**：安装并使用 **原生 arm64 Homebrew**（默认在 **`/opt/homebrew`**），然后：

  ```bash
  /opt/homebrew/bin/brew install pango gdk-pixbuf cairo
  rm -rf .venv && /opt/homebrew/bin/python3 -m venv .venv
  .venv/bin/pip install -r requirements-docs.txt
  ./scripts/local_pdf.sh
  ```

- **或**继续只用 `/usr/local` 的依赖时，用 **Rosetta 的 x86_64 Python** 建虚拟环境，例如：

  ```bash
  rm -rf .venv && arch -x86_64 /usr/local/bin/python3 -m venv .venv
  .venv/bin/pip install -r requirements-docs.txt
  ./scripts/local_pdf.sh
  ```

产物路径：**`site/pdf/<所选 .md 文件名的 stem>.pdf`**；CI 上为多份 **`site/pdf/<各变更 md 的 stem>.pdf`**。

**PDF 页眉 logo 水印**：默认使用 **`docs/static/espressif-standard-logo.png`**（部署/CI 前请确保该文件存在）。**更推荐 PNG**（尤其带 **Alpha** 的淡色水印，兼容性最好）。也可用环境变量 **`DOCFLOW_PDF_WATERMARK`** 指向其它路径。版式与尺寸见 **`docs/css/weasyprint-pdf.css`** 中 **`.docflow-pdf-margin-header`**。

**PDF 全页对角线底纹（如 CONFIDENTIAL）**：由 **`scripts/render_pdf.py`** 在生成 PDF 时注入，`position: fixed` 每页重复，**衬在正文之下**（浅红半透明，可调）。未设置环境变量时默认文案为 **`ESPRESSIF CONFIDENTIAL`**。执行 **`python scripts/render_pdf.py`**（或 CI 中同一步骤）前可设置 **`DOCFLOW_PDF_DIAGONAL_WATERMARK`** 为任意自定义字符串；设为 **`0`**、**`false`**、**`off`**、**`none`** 或**空串**则关闭。颜色、字号、倾角在 **`docs/css/weasyprint-pdf.css`** 的 **`--docflow-pdf-diagonal-watermark-color`**、**`--docflow-pdf-diagonal-watermark-size`**、**`--docflow-pdf-diagonal-watermark-angle`** 中修改。

**PDF 版式**集中在 **`docs/css/weasyprint-pdf.css`**：标题在 PDF 中为**纯黑**；任意标题若要在导出 PDF 时**从新页开始**，在标题行末加 **`{ .pdf-break-before }`**（需 **`mkdocs.yml`** 启用 **`attr_list`**），例如 `# 附录一 { .pdf-break-before }`。正文字体栈首选 **Helvetica Neue**（macOS 等已安装该字库的环境会直接用上）。GitHub Actions 的 Ubuntu 镜像**不能**附带 Apple 的 Helvetica Neue；**Helvetica Neue 字库本身不含中文**。本地 macOS 上 PDF 正文字体栈以 **Helvetica Neue** 优先，中文由 **PingFang SC** 等与 Helvetica 系搭配的系统无衬线按字形回退（与系统「用 Helvetica 排 UI、中文用苹方」一致）。workflow 会安装 **Nimbus Sans**、**Liberation Sans**（拉丁）及 **`fonts-noto-cjk`**（内含 **Noto Sans CJK SC** 等，Ubuntu 24.04 无单独的 `fonts-noto-cjk-sc` 包名），与 **`weasyprint-pdf.css`** 中的顺序一致。若需与某台机器完全一致，可在该机器上本地执行 **`./scripts/local_pdf.sh <docs 下路径.md>`**（脚本内会先单页构建再全量构建）。

仅预览站点可运行 `mkdocs serve`（不必装 WeasyPrint）。

## 仓库变量（Settings → Secrets and variables → Actions → Variables）

| 变量名 | 是否必填 | 说明 |
|--------|----------|------|
| `MKDOCS_SITE_URL` | 否 | 文档站点的公开根 URL（须以 `/` 结尾）。**不设置**时，CI 使用 `https://<owner>.github.io/<repo>/`（与默认 GitHub Pages 一致）。若使用自定义域名或 Pages 路径不是根路径，请设为实际地址，以便 MkDocs 与 PDF 中的链接正确。 |

在 **Settings → Pages** 中，将 **Build and deployment → Source** 选为 **GitHub Actions**。首次从本 workflow 部署后，站点与 PDF 的典型地址为：

- 站点首页：`https://<owner>.github.io/<repo>/`
- PDF：`https://<owner>.github.io/<repo>/pdf/<文件名>.pdf`（与 `docs` 下对应 `.md` 的 stem 一致；一次部署可包含多份）

### PR 里看不到 Checks / CI 没跑？

1. **目标分支要对**：workflow 只在「合并到 `main` / `master`」的 PR 上跑；若 PR 目标是别的分支，不会触发。
2. **workflow 文件必须在 PR 分支里**：把包含 `.github/workflows/pre_commit.yml` 的提交推上去；只改本地未推送不会出现 Checks。
3. **仓库已开启 Actions**：**Settings → Actions → General**，在 **Actions permissions** 里允许 **Actions**（组织仓库若被策略禁用，需管理员放行）。
4. **手动试跑**：在 **Actions** 页选中 **Pre-commit and docs**，用 **Run workflow**（需已加入 `workflow_dispatch`）确认能否跑通。

若主分支名字既非 `main` 也非 `master`，请编辑 workflow 里 `on:` 下的 `branches` 列表。
