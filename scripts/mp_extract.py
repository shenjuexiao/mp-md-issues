#!/usr/bin/env python3
"""提取公众号文章为 markdown，存储到 mp_md/{发布时间}_{文章标题}.md"""
import argparse
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def sanitize(name: str) -> str:
    """清理文件名非法字符"""
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name).strip()
    return name[:120] or "untitled"


def extract_article(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    content = soup.select_one("#js_content") or soup.select_one("article") or soup.body
    if not content:
        return "_无法提取正文内容_"

    # 清理脚本、样式
    for tag in content.select("script, style"):
        tag.decompose()

    html = str(content)
    text = md(html, heading_style="ATX", strip=["img"])
    # 折叠多余空行
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--readme", default="mp-readme.md")
    ap.add_argument("--output", default="mp_md")
    ap.add_argument("--changes", default="changes.json")
    args = ap.parse_args()

    changes = json.loads(Path(args.changes).read_text(encoding="utf-8"))
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = changes.get("added", []) + changes.get("updated", [])
    if not targets:
        print("没有新增或修改的文章，跳过提取。")
        return

    for item in targets:
        title = item["title"]
        pub_time = item["time"]
        link = item["link"]
        filename = f"{sanitize(pub_time)}_{sanitize(title)}.md"
        out_path = out_dir / filename

        if out_path.exists() and item in changes.get("updated", []):
            # 已存在且是更新，仍重新抓取覆盖
            pass

        try:
            print(f"抓取: {title} -> {link}")
            body = extract_article(link)
        except Exception as e:
            body = f"_抓取失败: {e}_"

        header = f"# {title}\n\n> 发布时间：{pub_time}  \n> 原文：[{link}]({link})\n\n---\n\n"
        out_path.write_text(header + body + "\n", encoding="utf-8")
        print(f"写入 {out_path}")


if __name__ == "__main__":
    main()