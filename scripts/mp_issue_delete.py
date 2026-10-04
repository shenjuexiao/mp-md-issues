#!/usr/bin/env python3
"""删除对应 Issue（mp-readme.md 中被删除的行）"""
import argparse
import json
import sys
from pathlib import Path

import requests


API = "https://api.github.com"


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
    ap.add_argument("--changes", default="changes.json")
    ap.add_argument("--token", required=True)
    args = ap.parse_args()

    changes = json.loads(Path(args.changes).read_text(encoding="utf-8"))
    removed = changes.get("removed", [])
    if not removed:
        print("没有删除的文章。")
        return

    for item in removed:
        title = item["title"]
        num = find_issue(args.repo, args.token, title)
        if not num:
            print(f"未找到 Issue: {title}，跳过删除")
            continue

        r = requests.patch(
            f"{API}/repos/{args.repo}/issues/{num}",
            headers=gh_headers(args.token),
            json={"state": "closed", "state_reason": "not_planned"},
        )
        if r.status_code == 200:
            print(f"关闭（视为删除）Issue #{num}: {title}")
        else:
            print(f"关闭失败 {title}: {r.status_code} {r.text}", file=sys.stderr)


if __name__ == "__main__":
    main()