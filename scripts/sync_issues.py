#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 .mp_diff.json 同步 Issues:
  added   -> 创建 Issue
  changed -> 更新 Issue（标题、正文、文件）
  removed -> 关闭并删除 Issue，删除本地 md 文件
状态保存在 .mp_state.json:
  { short_link: {"issue_number": n, "filename": "..."} }
"""
import json
import os
import re
from pathlib import Path

import requests

API = "https://api.github.com"
TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]  # owner/repo

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

DIFF = Path(".mp_diff.json")
STATE = Path(".mp_state.json")
MD_DIR = Path("mp_md")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip().replace(" ", "_")[:120] or "untitled"


def issue_body(info: dict, content: str) -> str:
    return (
        f"**发布时间**: {info['publish_time']}\n"
        f"**原文**: https://mp.weixin.qq.com/s/{info['short_link']}\n"
        f"**文件**: `mp_md/{info['filename']}`\n\n"
        f"---\n\n{content}"
    )


def create_issue(info: dict, content: str) -> int:
    r = requests.post(
        f"{API}/repos/{REPO}/issues",
        headers=HEADERS,
        json={
            "title": f"[MP] {info['title']}",
            "body": issue_body(info, content),
            "labels": ["mp-article"],
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["number"]


def update_issue(number: int, info: dict, content: str):
    r = requests.patch(
        f"{API}/repos/{REPO}/issues/{number}",
        headers=HEADERS,
        json={
            "title": f"[MP] {info['title']}",
            "body": issue_body(info, content),
        },
        timeout=30,
    )
    r.raise_for_status()


def delete_issue(number: int):
    # GitHub 没有直接删除 issue 的 REST 接口，先关闭再尝试 GraphQL 删除
    r = requests.patch(
        f"{API}/repos/{REPO}/issues/{number}",
        headers=HEADERS,
        json={"state": "closed"},
        timeout=30,
    )
    r.raise_for_status()

    # 可选：通过 GraphQL 真正删除 issue（需要 deleteIssue 权限）
    query = """
    mutation($id: ID!) { deleteIssue(input: {issueId: $id}) { clientMutationId } }
    """
    gql_headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    # 先拿 node_id
    info = requests.get(
        f"{API}/repos/{REPO}/issues/{number}",
        headers=HEADERS,
        timeout=30,
    ).json()
    node_id = info.get("node_id")
    if node_id:
        requests.post(
            "https://api.github.com/graphql",
            headers=gql_headers,
            json={"query": query, "variables": {"id": node_id}},
            timeout=30,
        )


def main():
    diff = json.loads(DIFF.read_text(encoding="utf-8"))
    curr = diff.get("curr", {})
    added = diff.get("added", [])
    changed = diff.get("changed", [])
    removed = diff.get("removed", [])

    state = load_state()

    # 1. 新增
    for short_link in added:
        info = curr[short_link]
        filename = f"{safe_filename(info['publish_time'])}_{safe_filename(info['title'])}.md"
        info["filename"] = filename
        content_path = MD_DIR / filename
        content = content_path.read_text(encoding="utf-8") if content_path.exists() else "_(无内容)_"
        number = create_issue(info, content)
        state[short_link] = {"issue_number": number, "filename": filename}
        print(f"[issues] created #{number} for {short_link}")

    # 2. 修改
    for short_link in changed:
        info = curr[short_link]
        filename = f"{safe_filename(info['publish_time'])}_{safe_filename(info['title'])}.md"
        info["filename"] = filename
        content_path = MD_DIR / filename
        content = content_path.read_text(encoding="utf-8") if content_path.exists() else "_(无内容)_"
        rec = state.get(short_link)
        if rec:
            update_issue(rec["issue_number"], info, content)
            rec["filename"] = filename
            print(f"[issues] updated #{rec['issue_number']} for {short_link}")
        else:
            number = create_issue(info, content)
            state[short_link] = {"issue_number": number, "filename": filename}
            print(f"[issues] recreated #{number} for {short_link}")

    # 3. 删除
    for short_link in removed:
        rec = state.pop(short_link, None)
        if rec:
            try:
                delete_issue(rec["issue_number"])
                print(f"[issues] deleted #{rec['issue_number']} for {short_link}")
            except Exception as e:
                print(f"[issues] delete failed #{rec['issue_number']}: {e}")
            f = MD_DIR / rec["filename"]
            if f.exists():
                f.unlink()
                print(f"[issues] removed file {f}")

    save_state(state)
    print("[issues] done")


if __name__ == "__main__":
    main()
