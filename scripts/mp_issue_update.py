#!/usr/bin/env python3
"""更新已有 Issue（对应被修改的行）"""
import argparse
import json
import re
import sys
from pathlib import Path

import requests


API = "https://api.github.com"


def sanitize(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name).strip()
    return name[:120] or "untitled"


def gh_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def find_issue(repo, token, title):
    q = f'repo:{repo} in:title is:issue "{title}"'
    r = requests.get(
        f"{API}/search/issues",
        headers=gh_headers(token),
        params={"q": q, "per_page": 20},
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
    updated = changes.get("updated", [])
    if not updated:
        print("没有修改的文章。")
        return

    md_dir = Path(args.md_dir)
    for item in updated:
        title = item["title"]
        pub_time = item["time"]
        link = item["link"]
        filename = f"{sanitize(pub_time)}_{sanitize(title)}.md"
        md_path = md_dir / filename
        body = md_path.read_text(encoding="utf-8") if md_path.exists() else \
               f"# {title}\n\n> 原文：[{link}]({link})\n"

        num = find_issue(args.repo, args.token, title)
        if not num:
            print(f"未找到 Issue: {title}，跳过更新")
            continue

        r = requests.patch(
            f"{API}/repos/{args.repo}/issues/{num}",
            headers=gh_headers(args.token),
            json={"body": body},
        )
        if r.status_code == 200:
            print(f"更新 Issue #{num}: {title}")
        else:
            print(f"更新失败 {title}: {r.status_code} {r.text}", file=sys.stderr)


if __name__ == "__main__":
    main()