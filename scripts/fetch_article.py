#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 .mp_diff.json 中 added 的短链接抓取公众号文章，转 Markdown，
保存为 mp_md/{publish_time}_{title}.md
"""
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

DIFF = Path(".mp_diff.json")
MD_DIR = Path("mp_md")
MD_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def safe_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip().replace(" ", "_")
    return name[:120] or "untitled"


def fetch(short_link: str) -> str:
    url = f"https://mp.weixin.qq.com/s/{short_link}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    node = soup.select_one("#js_content") or soup.select_one(".rich_media_content")
    if not node:
        # 兜底：把 body 转 md
        node = soup.body or soup

    for tag in node.select("script, style"):
        tag.decompose()

    # 图片补全 src（微信 data-src 懒加载）
    for img in node.find_all("img"):
        src = img.get("data-src") or img.get("src")
        if src:
            img["src"] = src

    return md(str(node), heading_style="ATX").strip()


def main():
    data = json.loads(DIFF.read_text(encoding="utf-8"))
    added = data.get("added", [])
    curr = data.get("curr", {})

    for short_link in added:
        info = curr.get(short_link)
        if not info:
            continue
        title = info["title"]
        publish_time = info["publish_time"]
        filename = f"{safe_filename(publish_time)}_{safe_filename(title)}.md"
        out_path = MD_DIR / filename
        if out_path.exists():
            print(f"[fetch] skip existing {out_path}")
            continue

        try:
            content = fetch(short_link)
        except Exception as e:
            content = f"> 抓取失败: {e}\n\n原文: https://mp.weixin.qq.com/s/{short_link}"

        header = (
            f"# {title}\n\n"
            f"- 发布时间: {publish_time}\n"
            f"- 原文: https://mp.weixin.qq.com/s/{short_link}\n\n"
            f"---\n\n"
        )
        out_path.write_text(header + content, encoding="utf-8")
        print(f"[fetch] saved {out_path}")
        time.sleep(2)  # 简单限速，降低被封风险


if __name__ == "__main__":
    main()
