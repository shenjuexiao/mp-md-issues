# scripts/mp_extract-0.0.2.py
# github.com/shenjuexiao
# 20261004

# scripts/mp_extract.py
#!/usr/bin/env python3
"""提取公众号文章为 markdown，存储到 mp_md/{发布时间}_{文章标题}.md"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

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


def extract_author(soup: BeautifulSoup) -> str:
    """从页面中提取作者名"""
    for sel in (
        "#js_name",
        ".rich_media_meta.rich_media_meta_text",
        "#meta_content .rich_media_meta_text",
    ):
        node = soup.select_one(sel)
        if node:
            text = node.get_text(strip=True)
            if text:
                return text

    meta = soup.find("meta", attrs={"name": "author"})
    if meta and meta.get("content"):
        return meta["content"].strip()

    return "未知"


def normalize_images(content: BeautifulSoup) -> None:
    """将微信懒加载图片的 data-src 提升为 src，并去掉无意义属性"""
    for img in content.find_all("img"):
        # 微信常见懒加载属性
        for attr in ("data-src", "data-original", "data-backsrc"):
            real = img.get(attr)
            if real:
                img["src"] = real
                break

        # 若仍无 src，尝试从 srcset 取第一个
        if not img.get("src") and img.get("srcset"):
            first = img["srcset"].split(",")[0].strip().split(" ")[0]
            if first:
                img["src"] = first

        # 清理多余属性，避免生成噪声
        for attr in list(img.attrs):
            if attr not in ("src", "alt", "title"):
                del img[attr]

        # 补全相对路径
        if img.get("src") and not re.match(r"^(https?:)?//", img["src"]):
            img["src"] = urljoin("https://mp.weixin.qq.com/", img["src"])


def extract_article(url: str):
    """返回 (正文 markdown, 作者)"""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    author = extract_author(soup)

    content = soup.select_one("#js_content") or soup.select_one("article") or soup.body
    if not content:
        return "_无法提取正文内容_", author

    # 清理脚本、样式
    for tag in content.select("script, style"):
        tag.decompose()

    # 处理图片（关键修复：保留图片）
    normalize_images(content)

    html = str(content)
    # 注意：不再 strip=["img"]，图片会被转换为 ![alt](src)
    text = md(html, heading_style="ATX")
    # 折叠多余空行
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, author


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

        try:
            print(f"抓取: {title} -> {link}")
            body, author = extract_article(link)
        except Exception as e:
            body, author = f"_抓取失败: {e}_", "未知"

        header = (
            f"# {title}\n\n"
            f"> 发布时间：{pub_time}  \n"
            f"> 作者：{author}  \n"
            f"> 原文：[{link}]({link})\n\n"
            f"---\n\n"
        )
        out_path.write_text(header + body + "\n", encoding="utf-8")
        print(f"写入 {out_path}")


if __name__ == "__main__":
    main()
