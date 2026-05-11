# 🚀 GitHub Trending 每日幽默点评

> AI 每天早上自动抓取 GitHub Trending，用幽默风格生成博文，部署在 GitHub Pages。

**[在线预览 →](https://你的用户名.github.io/github-trending-blog)**

## ✨ 特性

- 🕷️ **自动抓取** — 每日 UTC 0:00 自动爬取 GitHub Trending
- 🤖 **AI 写段子** — 用 LLM 为每个热门项目写幽默点评
- 🎨 **极简设计** — Vercel 风格，Geist 字体，响应式布局
- ⚡ **零成本部署** — GitHub Pages + Actions，完全免费
- 📡 **RSS 订阅** — 支持 RSS 阅读器订阅

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角 Fork，然后 clone 到本地：

```bash
git clone https://github.com/你的用户名/github-trending-blog.git
cd github-trending-blog
```

### 2. 配置 API Key（可选，推荐）

设置 OpenAI API Key 以启用 AI 幽默写作。没有也能运行（使用模板化段子）。

在仓库的 **Settings → Secrets and variables → Actions** 中添加：

| Secret | 说明 | 必填 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | 推荐 |
| `OPENAI_BASE_URL` | 自定义 API 端点（如 DeepSeek、OpenRouter） | 可选 |
| `LLM_MODEL` | 模型名称（默认 `gpt-4o-mini`） | 可选 |

支持任何 OpenAI 兼容接口：

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# DeepSeek
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# OpenRouter
OPENAI_API_KEY=sk-or-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4o-mini
```

### 3. 启用 GitHub Pages

1. 进入仓库 **Settings → Pages**
2. Source 选择 **Deploy from a branch**
3. Branch 选择 `gh-pages`，目录 `/ (root)`
4. 点击 Save

### 4. 触发首次构建

进入 **Actions** 标签，选择 **Daily GitHub Trending Blog**，点击 **Run workflow**。

几分钟后，你的博客就上线了！🎉

## 🏗️ 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 1. 抓取 GitHub Trending
python scraper.py

# 2. 生成博文（需要 API Key 或用模板模式）
OPENAI_API_KEY=sk-... python generate.py

# 3. 构建静态站点
python build.py

# 4. 本地预览
python build.py --serve
# 打开 http://localhost:8080
```

## 📁 项目结构

```
├── scraper.py              # 爬虫：抓取 GitHub Trending
├── generate.py             # 生成：LLM 写幽默博文
├── build.py                # 构建：生成静态 HTML
├── templates/              # Jinja2 模板
│   ├── base.html           #   基础布局
│   ├── index.html          #   首页
│   ├── post.html           #   文章页
│   └── archive.html        #   归档页
├── static/
│   └── style.css           # Vercel 风格样式
├── data/                   # 原始 JSON 数据（自动生成）
├── posts/                  # Markdown 博文（自动生成）
├── output/                 # 静态 HTML（自动生成）
├── .github/workflows/
│   └── daily.yml           # GitHub Actions 自动化
└── requirements.txt
```

## 🛠️ 自定义

### 修改设计

编辑 `templates/` 和 `static/style.css`。设计灵感来自 Vercel：
- Geist 字体 + 黑白极简
- Shadow-as-border 技巧
- 响应式三色（Develop Blue / Preview Pink / Ship Red）

### 修改博文风格

编辑 `generate.py` 中的 `SYSTEM_PROMPT`，自定义 AI 的写作风格。

### 手动回填

```bash
# 回填历史数据
python scraper.py 2026-05-10
python generate.py 2026-05-10
python build.py
```

## 📄 License

MIT
