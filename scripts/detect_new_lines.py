#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测 mp-readme.md 中新增的文章行。
格式：文章标题|发布时间|短链接
状态保存在 .github/state/mp_readme_state.json
输出：new_lines.json，并设置 has_new 输出变量
"""

import json
import os
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
README = WORKSPACE / "mp-readme.md"
STATE_DIR = WORKSPACE / ".github" / "state"
STATE_FILE = STATE_DIR / "mp_readme_state.json"
NEW_LINES_FILE = WORKSPACE / "new_lines.json"


def parse_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 3:
        return None
    title, pub_time, short_link = parts[0], parts[1], parts[2]
    # 兼容完整链接，只取 /s/ 后面的部分
    if "/s/" in short_link:
        short_link = short_link.split("/s/")[-1].split("?")[0].strip()
    return {
        "title": title,
        "pub_time": pub_time,
        "short_link": short_link,
    }


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"processed": []}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def set_output(name, value):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"[output] {name}={value}")


def main():
    if not README.exists():
        print(f"ERROR: {README} not found")
        set_output("has_new", "false")
        sys.exit(0)

    state = load_state()
    processed = set(state.get("processed", []))

    new_items = []
    all_links = []

    for line in README.read_text(encoding="utf-8").splitlines():
        item = parse_line(line)
        if not item:
            continue
        key = item["short_link"]
        all_links.append(key)
        if key not in processed:
            new_items.append(item)

    if new_items:
        print(f"Detected {len(new_items)} new article(s):")
        for it in new_items:
            print(f"  - {it['pub_time']} | {it['title']} | {it['short_link']}")
    else:
        print("No new articles detected.")

    NEW_LINES_FILE.write_text(
        json.dumps(new_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 状态中记录所有已出现过的链接
    state["processed"] = sorted(set(processed) | set(all_links))
    save_state(state)

    set_output("has_new", "true" if new_items else "false")


if __name__ == "__main__":
    main()