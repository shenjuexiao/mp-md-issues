# scripts/mp_issue_create-0.0.0.py
# github.com/shenjuexiao
# 20261004

# v0.0.0-20261004
# chat.deepseek.com/a/chat/s/c27d6549-bdeb-497b-889d-3873dd7a6efc

#!/usr/bin/env python3
"""为新增文章创建 Issue，标签 MP"""
import argparse
import json
import sys
from pathlib import Path

import requests


API = "https://api.github.com"


def sanitize(name: str) -> str:
    import re
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name).strip()
    return name[:120] or "untitled"


def gh_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def ensure_label(repo, token, label="MP", color="1d76db"):
    url = f"{API}/repos/{repo}/labels"
    r = requests.get(f"{url}/{label}", headers=gh_headers(token))
    if r.status_code == 404:
        requests.post(
            url,
            headers=gh_headers(token),
            json={"name": label, "color": color, "description": "微信公众号文章"},
        )
        print(f"创建标签: {label}")
    else:
        print(f"标签已存在: {label}")


def issue_exists(repo, token, title):
    """通过搜索是否存在同标题的开启 Issue"""
    q = f'repo:{repo} in:title is:issue is:open "{title}"'
    r = requests.get(
        f"{API}/search/issues",
        headers=gh_headers(token),
        params={"q": q, "per_page": 5},
    )
    if r.status_code != 200:
        return None
    for it in r.json().get("items", []):
        if it["title"] == title:
            return it["number"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--readme", default="mp-readme.md")
    ap.add_argument("--md-dir", default="mp_md")
    ap.add_argument("--changes", default="changes.json")
    ap.add_argument("--token", required=True)
    args = ap.parse_args()

    changes = json.loads(Path(args.changes).read_text(encoding="utf-8"))
    added = changes.get("added", [])
    if not added:
        print("没有新增文章。")
        return

    ensure_label(args.repo, args.token)

    md_dir = Path(args.md_dir)
    for item in added:
        title = item["title"]
        pub_time = item["time"]
        link = item["link"]
        filename = f"{sanitize(pub_time)}_{sanitize(title)}.md"
        md_path = md_dir / filename
        body = md_path.read_text(encoding="utf-8") if md_path.exists() else \
               f"# {title}\n\n> 原文：[{link}]({link})\n"

        # 避免重复
        existing = issue_exists(args.repo, args.token, title)
        if existing:
            print(f"已存在 Issue #{existing}: {title}，跳过")
            continue

        r = requests.post(
            f"{API}/repos/{args.repo}/issues",
            headers=gh_headers(args.token),
            json={"title": title, "body": body, "labels": ["MP"]},
        )
        if r.status_code in (200, 201):
            print(f"创建 Issue: {title} -> #{r.json()['number']}")
        else:
            print(f"创建失败 {title}: {r.status_code} {r.text}", file=sys.stderr)


if __name__ == "__main__":
    main()