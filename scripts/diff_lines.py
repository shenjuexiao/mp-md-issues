#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比 mp-readme.md 的上一版本与当前版本，得出:
  added:   新增的 short_link 列表
  removed: 删除的 short_link 列表
  changed: 标题/时间发生变化的 short_link 列表
输出: .mp_diff.json
并写 has_new=true/false 到 $GITHUB_OUTPUT
"""
import json
import os
import re
import subprocess
from pathlib import Path

README = "mp-readme.md"
DIFF_OUT = Path(".mp_diff.json")

SHORT_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s/([A-Za-z0-9_\-]+)")


def parse_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 3:
        return None
    m = SHORT_RE.search(parts[2])
    if not m:
        return None
    return {
        "title": parts[0],
        "publish_time": parts[1],
        "short_link": m.group(1),
        "raw": line,
    }


def git_show_prev():
    """取 HEAD^ 版本的 mp-readme.md，若不存在返回空字符串"""
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD^:{README}"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8")
    except subprocess.CalledProcessError:
        return ""


def main():
    prev_text = git_show_prev()
    curr_text = Path(README).read_text(encoding="utf-8")

    prev_map = {}
    for line in prev_text.splitlines():
        it = parse_line(line)
        if it:
            prev_map[it["short_link"]] = it

    curr_map = {}
    for line in curr_text.splitlines():
        it = parse_line(line)
        if it:
            curr_map[it["short_link"]] = it

    added = [k for k in curr_map if k not in prev_map]
    removed = [k for k in prev_map if k not in curr_map]
    changed = [
        k for k in curr_map
        if k in prev_map and (
            curr_map[k]["title"] != prev_map[k]["title"]
            or curr_map[k]["publish_time"] != prev_map[k]["publish_time"]
        )
    ]

    result = {
        "added": added,
        "removed": removed,
        "changed": changed,
        "curr": curr_map,
        "prev": prev_map,
    }
    DIFF_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[diff] added={added} removed={removed} changed={changed}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"has_new={'true' if added else 'false'}\n")


if __name__ == "__main__":
    main()
