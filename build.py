#!/usr/bin/env python3
"""
Static Site Builder

Converts Markdown posts + Jinja2 templates → static HTML for GitHub Pages.

Usage:
  python build.py              # Build all posts
  python build.py --serve      # Build + start local server
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
POSTS_DIR = ROOT / "posts"
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"
STATIC_DIR = ROOT / "static"

env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


def _parse_markdown_post(md_path: Path) -> dict:
    """Parse a markdown post, extracting title and converting to HTML."""
    raw = md_path.read_text()

    # Extract date from filename: YYYY-MM-DD-github-trending.md
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", md_path.stem)
    post_date = date_match.group(1) if date_match else "unknown"

    # Extract title (first # heading)
    title = "GitHub Trending"
    body = raw
    title_match = re.match(r"^#\s+(.+)$", raw, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        # Remove the title line from body (already in template)
        body = raw[title_match.end():].strip()

    # Convert basic markdown to HTML (simple approach — handles most LLM output)
    html = _md_to_html(body)

    # Extract first paragraph as excerpt
    excerpt = ""
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith(">"):
            excerpt = stripped[:200]
            if len(stripped) > 200:
                excerpt += "..."
            break

    return {
        "date": post_date,
        "title": title,
        "slug": post_date,
        "excerpt": excerpt,
        "html": html,
    }


def _md_to_html(md_text: str) -> str:
    """Very basic markdown-to-HTML converter. Handles LLM output well enough."""
    lines = md_text.split("\n")
    result = []
    in_code_block = False
    in_list = False

    for line in lines:
        stripped = line.rstrip()

        # Code blocks
        if stripped.startswith("```"):
            if in_code_block:
                result.append("</code></pre>")
                in_code_block = False
            else:
                result.append('<pre><code>')
                in_code_block = True
            continue

        if in_code_block:
            result.append(_escape_html(stripped))
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            result.append("<hr>")
            continue

        # Headings
        if stripped.startswith("### "):
            result.append(f"<h3>{_escape_html(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            result.append(f"<h2>{_escape_html(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            # Skip — title is handled by template
            continue

        # Blockquote
        if stripped.startswith("> "):
            content = _inline_md(stripped[2:])
            result.append(f"<blockquote>{content}</blockquote>")
            continue

        # Unordered list
        if re.match(r"^[\-\*]\s+", stripped):
            content = _inline_md(re.sub(r"^[\-\*]\s+", "", stripped))
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(f"<li>{content}</li>")
            continue
        else:
            if in_list:
                result.append("</ul>")
                in_list = False

        # Emphasis / bold markers
        if stripped.startswith("**") and stripped.endswith("**"):
            content = _escape_html(stripped[2:-2])
            result.append(f'<p class="bold-line"><strong>{content}</strong></p>')
            continue

        # Regular paragraph
        if stripped:
            result.append(f"<p>{_inline_md(stripped)}</p>")
        elif not in_list:
            # Empty line — paragraph break
            pass

    if in_list:
        result.append("</ul>")
    if in_code_block:
        result.append("</code></pre>")

    return "\n".join(result)


def _inline_md(text: str) -> str:
    """Handle inline markdown: **bold**, *italic*, `code`, [links](url)."""
    # Escaped HTML first
    text = _escape_html(text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Bold
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def collect_posts() -> list[dict]:
    """Collect all posts, sorted by date descending."""
    posts = []
    if POSTS_DIR.exists():
        for md_file in sorted(POSTS_DIR.glob("*.md"), reverse=True):
            try:
                post = _parse_markdown_post(md_file)
                posts.append(post)
            except Exception as e:
                print(f"  Warning: skipping {md_file.name} — {e}", file=sys.stderr)
    return posts


def copy_static():
    """Copy static assets to output."""
    dest = OUTPUT_DIR / "static"
    dest.mkdir(parents=True, exist_ok=True)
    if STATIC_DIR.exists():
        for f in STATIC_DIR.iterdir():
            if f.is_file():
                (dest / f.name).write_bytes(f.read_bytes())
                print(f"  Copied static/{f.name}")


def build():
    """Build the entire site."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "posts").mkdir(parents=True, exist_ok=True)

    posts = collect_posts()
    print(f"Found {len(posts)} posts")

    copy_static()

    # --- Homepage ---
    recent_posts = posts[:7]  # Show last 7 days
    homepage = env.get_template("index.html").render(
        posts=recent_posts,
        total_posts=len(posts),
        generated_at=date.today().isoformat(),
    )
    (OUTPUT_DIR / "index.html").write_text(homepage)
    print("  Built index.html")

    # --- Individual posts ---
    post_template = env.get_template("post.html")
    for post in posts:
        post_html = post_template.render(
            post=post,
            generated_at=date.today().isoformat(),
        )
        (OUTPUT_DIR / "posts" / f"{post['slug']}.html").write_text(post_html)
    print(f"  Built {len(posts)} post pages")

    # --- Archive ---
    archive = env.get_template("archive.html").render(
        posts=posts,
        total_posts=len(posts),
        generated_at=date.today().isoformat(),
    )
    (OUTPUT_DIR / "archive.html").write_text(archive)
    print("  Built archive.html")

    # --- RSS Feed ---
    rss = _build_rss(posts)
    (OUTPUT_DIR / "feed.xml").write_text(rss)
    print("  Built feed.xml")

    print(f"\nDone! Site built in {OUTPUT_DIR}")


def _build_rss(posts: list[dict]) -> str:
    """Generate a simple RSS 2.0 feed."""
    SITE_URL = "https://trending.dev"  # Placeholder — user should update
    items = []
    for post in posts[:20]:
        items.append(f"""    <item>
      <title>{_escape_html(post['title'])}</title>
      <link>{SITE_URL}/posts/{post['slug']}.html</link>
      <description>{_escape_html(post['excerpt'])}</description>
      <pubDate>{post['date']}T00:00:00Z</pubDate>
      <guid>{SITE_URL}/posts/{post['slug']}.html</guid>
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>GitHub Trending 幽默点评</title>
    <link>{SITE_URL}</link>
    <description>每日 GitHub Trending 幽默点评——AI 写段子，程序员图一乐</description>
    <language>zh-CN</language>
{chr(10).join(items)}
  </channel>
</rss>"""


def main():
    if "--serve" in sys.argv:
        build()
        import http.server
        import socketserver
        import os
        os.chdir(OUTPUT_DIR)
        port = 8080
        print(f"\nServing at http://localhost:{port}")
        with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down.")
    else:
        build()


if __name__ == "__main__":
    main()
