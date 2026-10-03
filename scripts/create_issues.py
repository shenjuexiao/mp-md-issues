#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 mp_md 文件夹中新增的 markdown 文件作为 Issue 发布。
Issue 标题：文章标题
Issue 内容：markdown 文件内容
已存在同名 Issue 则跳过。
"""

import json
import os
import time
from pathlib import Path

import requests

WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
NEW_LINES_FILE = WORKSPACE / "new_lines.json"
MP_MD_DIR = WORKSPACE / "mp_md"

TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY")
API = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def sanitize_filename(name: str, max_len: int = 80) -> str:
    import re
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name)
    name = re.sub(r"\s+", " ", name).strip().replace(" ", "_")
    return name[:max_len] or "untitled"


def normalize_date(pub_time: str) -> str:
    import re
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", pub_time)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return sanitize_filename(pub_time)


def list_existing_issues():
    titles = set()
    page = 1
    while True:
        resp = requests.get(
            f"{API}/repos/{REPO}/issues",
            headers=HEADERS,
            params={"state": "all", "per_page": 100, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        for it in data:
            if "pull_request" in it:
                continue
            titles.add(it["title"].strip())
        if len(data) < 100:
            break
        page += 1
    return titles


def create_issue(title, body):
    resp = requests.post(
        f"{API}/repos/{REPO}/issues",
        headers=HEADERS,
        json={"title": title, "body": body},
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"创建 Issue 失败：{resp.status_code} {resp.text}")
    return resp.json()


def main():
    if not TOKEN:
        raise SystemExit("缺少 GITHUB_TOKEN")
    if not REPO:
        raise SystemExit("缺少 GITHUB_REPOSITORY")

    if not NEW_LINES_FILE.exists():
        print("new_lines.json 不存在，跳过")
        return

    items = json.loads(NEW_LINES_FILE.read_text(encoding="utf-8"))
    if not items:
        print("没有新文章需要发布")
        return

    existing = list_existing_issues()
    print(f"已存在 {len(existing)} 个 Issue")

    for item in items:
        title = item["title"]
        pub_time = item["pub_time"]
        date_str = normalize_date(pub_time)
        safe_title = sanitize_filename(title)
        filename = f"{date_str}_{safe_title}.md"
        path = MP_MD_DIR / filename

        if not path.exists():
            print(f"文件不存在，跳过：{path.name}")
            continue

        if title.strip() in existing:
            print(f"Issue 已存在，跳过：{title}")
            continue

        body = path.read_text(encoding="utf-8")
        # GitHub Issue body 有大小限制（约 65536 字符）
        if len(body) > 60000:
            body = body[:60000] + "\n\n... (内容过长已截断)"

        try:
            issue = create_issue(title, body)
            print(f"已创建 Issue #{issue['number']}：{title}")
            existing.add(title.strip())
        except Exception as e:
            print(f"创建 Issue 失败：{title} -> {e}")

        time.sleep(1)


if __name__ == "__main__":
    main()