#!/usr/bin/env python3
"""检测 mp-readme.md 相对于上一次提交的变化"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


README = "mp-readme.md"


def parse_lines(text: str):
    """解析 readme 行为 {key: line}，key = 标题"""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        title, pub_time, link = parts[0], parts[1], parts[2]
        result[title] = {"title": title, "time": pub_time, "link": link, "raw": line}
    return result


def get_file_at_ref(ref: str) -> str:
    if not ref or ref == "0" * 40:
        return ""
    try:
        out = subprocess.check_output(
            ["git", "show", f"{ref}:{README}"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8")
    except subprocess.CalledProcessError:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before")
    ap.add_argument("--after")
    ap.add_argument("--mode", default="diff")
    ap.add_argument("--out", default="changes.json")
    args = ap.parse_args()

    if args.mode == "full":
        after_text = Path(README).read_text(encoding="utf-8")
        old_map = {}
        new_map = parse_lines(after_text)
        added = list(new_map.keys())
        updated, removed = [], []
    else:
        before_text = get_file_at_ref(args.before) if args.before else ""
        after_text = Path(README).read_text(encoding="utf-8")
        old_map = parse_lines(before_text)
        new_map = parse_lines(after_text)

        added, updated, removed = [], [], []
        for title, info in new_map.items():
            if title not in old_map:
                added.append(title)
            elif old_map[title]["raw"] != info["raw"]:
                updated.append(title)
        for title in old_map:
            if title not in new_map:
                removed.append(title)

    changes = {
        "added": [{"title": t, **new_map[t]} for t in added if t in new_map],
        "updated": [{"title": t, **new_map[t]} for t in updated if t in new_map],
        "removed": [{"title": t, **old_map[t]} for t in removed if t in old_map],
    }
    Path(args.out).write_text(
        json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(changes, ensure_ascii=False, indent=2))

    # 输出给后续步骤
    if "GITHUB_OUTPUT" in __import__("os").environ:
        with open(__import__("os").environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"added_count={len(added)}\n")
            f.write(f"updated_count={len(updated)}\n")
            f.write(f"removed_count={len(removed)}\n")


if __name__ == "__main__":
    main()