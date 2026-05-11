#!/usr/bin/env python3
"""
GitHub Trending Blog Generator

Reads trending JSON data and uses an LLM to generate humorous blog posts in Markdown.

Environment variables:
  OPENAI_API_KEY   — required for LLM generation
  OPENAI_BASE_URL  — optional custom endpoint (DeepSeek, OpenRouter, etc.)
  LLM_MODEL        — model name (default: gpt-4o-mini)

Output: posts/YYYY-MM-DD-github-trending.md
"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
POSTS_DIR = Path(__file__).parent / "posts"

# --- LLM Prompt Templates ---

SYSTEM_PROMPT = """你是一个幽默风趣的科技博主，专门写 GitHub Trending 每日点评。

## 你的风格
- 用中文写作，语气轻松幽默，像跟程序员朋友聊天
- 给每个项目起一个搞笑的外号或一句话总结
- 善用比喻、夸张、自嘲、冷笑话
- 可以吐槽，但要保持善意（我们都是写代码的）
- 每篇文章控制在 800-1500 字
- 文章标题要有吸引力

## 文章结构
1. 一个吸引眼球的标题（带 emoji）
2. 一句话开篇段子
3. 每个项目的点评（不需要全部，挑 8-10 个最有意思的）
   - 项目名称 + 链接
   - 一句话总结（语言、stars、今日新增）
   - 幽默点评（2-3 句）
4. 结尾总结段子

## 输出格式：纯 Markdown，不要用代码块包裹
"""

USER_PROMPT_TEMPLATE = """以下是 {date} GitHub Trending 今日热门项目（共 {count} 个），请写一篇幽默点评博文：

{trending_list}"""


def _build_trending_text(repos: list[dict], max_repos: int = 15) -> str:
    """Format repo list as text for the prompt."""
    lines = []
    for i, repo in enumerate(repos[:max_repos], 1):
        lines.append(
            f"{i}. **{repo['full_name']}**\n"
            f"   语言: {repo['language']} | ⭐ {repo['stars']:,} | 今日新增: +{repo['stars_today']:,}\n"
            f"   描述: {repo['description'] or '(无描述)'}\n"
        )
    return "\n".join(lines)


def generate_with_llm(repos: list[dict], target_date: str) -> str:
    """Call an OpenAI-compatible API to generate the blog post."""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. "
            "Set it via: export OPENAI_API_KEY=sk-...\n"
            "For DeepSeek: export OPENAI_BASE_URL=https://api.deepseek.com/v1\n"
            "For OpenRouter: export OPENAI_BASE_URL=https://openrouter.ai/api/v1"
        )

    from openai import OpenAI

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url.rstrip("/") + "/"
    client = OpenAI(**client_kwargs)

    trending_text = _build_trending_text(repos)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        date=target_date,
        count=min(len(repos), 15),
        trending_list=trending_text,
    )

    print(f"  Calling {model} to generate post ...")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=4096,
    )

    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned empty response")

    # Clean up: strip markdown code fences if the model wrapped the output
    content = content.strip()
    if content.startswith("```markdown"):
        content = content[len("```markdown"):].strip()
    if content.startswith("```"):
        content = content[3:].strip()
    if content.endswith("```"):
        content = content[:-3].strip()

    return content


def generate_fallback(repos: list[dict], target_date: str) -> str:
    """Template-based fallback when no LLM API key is available."""
    import random

    jokes = [
        "这个项目告诉我们：写代码的最高境界是让别人帮你写。",
        "又一款\"用 Rust 重写一切\"的作品，Rustaceans 们狂喜。",
        "看这 star 增速，怕是比我的年终奖涨得还快。",
        "README 写得比代码还长，这就是开源精神。",
        "以\"轻量级\"自称的项目通常重得你怀疑人生。",
    ]
    emoji_pool = ["🔥", "🚀", "💡", "🤖", "🌈", "⚡", "🦀", "🐍", "🎯", "💎"]

    lines = [
        f"# 🚀 GitHub 今日热榜 —— {target_date}",
        "",
        "> 程序员们今天又在 star 什么奇怪的东西？让我们一探究竟！",
        "",
        f"_⚠️ 本文由模板自动生成（未配置 LLM API key）。设置 OPENAI_API_KEY 即可启用 AI 幽默写作。_",
        "",
    ]

    for repo in repos[:10]:
        emoji = random.choice(emoji_pool)
        lines.extend([
            f"## {emoji} [{repo['full_name']}]({repo['url']})",
            "",
            f"**语言**：{repo['language']} | ⭐ {repo['stars']:,} | 今日 +{repo['stars_today']:,}",
            "",
            f"> {repo['description'] or '这个项目太神秘了，连描述都没有。'}",
            "",
            random.choice(jokes),
            "",
        ])

    lines.extend([
        "---",
        f"*本文由 GitHub Trending Bot 自动生成 · 数据来源：[GitHub Trending](https://github.com/trending)*",
    ])
    return "\n".join(lines)


def save_post(content: str, target_date: str) -> Path:
    """Save the generated post as Markdown."""
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    path = POSTS_DIR / f"{target_date}-github-trending.md"
    path.write_text(content)
    print(f"  Saved post to {path}")
    return path


def main():
    today = date.today().isoformat()

    # Check for a date argument (for backfilling)
    target_date = sys.argv[1] if len(sys.argv) > 1 else today

    data_path = DATA_DIR / f"trending-{target_date}.json"
    if not data_path.exists():
        print(f"Error: {data_path} not found. Run scraper.py first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(data_path.read_text())
    repos = data["repositories"]

    # Try LLM first, fall back to template
    try:
        content = generate_with_llm(repos, target_date)
    except RuntimeError as e:
        print(f"  LLM unavailable: {e}")
        print("  Falling back to template-based generation.")
        content = generate_fallback(repos, target_date)

    save_post(content, target_date)


if __name__ == "__main__":
    main()
