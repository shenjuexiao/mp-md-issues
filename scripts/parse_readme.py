#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 mp-readme.md
格式: 文章标题|发布时间|短链接
输出: .mp_parsed.json
    [{"title":..., "publish_time":..., "short_link":..., "raw": 原始行}, ...]
"""
import json
import re
from pathlib import Path

README = Path("mp-readme.md")
OUT = Path(".mp_parsed.json")

# 短链接: https://mp.weixin.qq.com/s/xxxx
SHORT_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s/([A-Za-z0-9_\-]+)")


def parse_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 3:
        return None
    title, publish_time, link = parts[0], parts[1], parts[2]
    m = SHORT_RE.search(link)
    if not m:
        return None
    return {
        "title": title,
        "publish_time": publish_time,
        "short_link": m.group(1),
        "raw": line,
    }


def main():
    items = []
    for line in README.read_text(encoding="utf-8").splitlines():
        item = parse_line(line)
        if item:
            items.append(item)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[parse_readme] parsed {len(items)} items")


if __name__ == "__main__":
    main()
