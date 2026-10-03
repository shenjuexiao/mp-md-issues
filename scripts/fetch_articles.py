#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据短链接抓取微信公众号文章，转化为 Markdown。
输出：mp_md/发布时间_文章标题.md
"""

import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
NEW_LINES_FILE = WORKSPACE / "new_lines.json"
MP_MD_DIR = WORKSPACE / "mp_md"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def sanitize_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.replace(" ", "_")
    if len(name) > max_len:
        name = name[:max_len]
    return name or "untitled"


def normalize_date(pub_time: str) -> str:
    """把 2024-01-01 / 2024/01/01 / 2024年01月01日 等统一成 YYYY-MM-DD"""
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", pub_time)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return sanitize_filename(pub_time)


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def extract_content(html: str):
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h1", id="activity-name") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    author_tag = soup.find("a", id="js_name") or soup.find("span", id="js_name")
    author = author_tag.get_text(strip=True) if author_tag else ""

    content = soup.find("div", id="js_content") or soup.find("div", class_="rich_media_content")
    if content is None:
        raise RuntimeError("未找到文章正文 (#js_content)")

    # 处理图片懒加载
    for img in content.find_all("img"):
        src = img.get("data-src") or img.get("src")
        if src:
            img["src"] = src
        img.attrs.pop("data-src", None)

    body_md = md(str(content), heading_style="ATX", bullets="-")
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()

    return title, author, body_md


def build_markdown(title, author, pub_time, short_link, body_md):
    url = f"https://mp.weixin.qq.com/s/{short_link}"
    header = f"# {title}\n\n"
    meta = f"> 发布时间：{pub_time}\n>\n> 作者：{author or '未知'}\n>\n> 原文：[{url}]({url})\n\n---\n\n"
    return header + meta + body_md + "\n"


def main():
    if not NEW_LINES_FILE.exists():
        print("new_lines.json 不存在，跳过")
        return

    items = json.loads(NEW_LINES_FILE.read_text(encoding="utf-8"))
    if not items:
        print("没有新文章需要抓取")
        return

    MP_MD_DIR.mkdir(parents=True, exist_ok=True)

    for item in items:
        title = item["title"]
        pub_time = item["pub_time"]
        short_link = item["short_link"]
        url = f"https://mp.weixin.qq.com/s/{short_link}"

        date_str = normalize_date(pub_time)
        safe_title = sanitize_filename(title)
        filename = f"{date_str}_{safe_title}.md"
        out_path = MP_MD_DIR / filename

        if out_path.exists():
            print(f"已存在，跳过：{out_path.name}")
            continue

        print(f"抓取：{url}")
        try:
            html = fetch_html(url)
            real_title, author, body_md = extract_content(html)
            final_title = real_title or title
            content = build_markdown(final_title, author, pub_time, short_link, body_md)
            out_path.write_text(content, encoding="utf-8")
            print(f"已保存：{out_path.name}")
        except Exception as e:
            print(f"抓取失败：{url} -> {e}")

        time.sleep(2)


if __name__ == "__main__":
    main()