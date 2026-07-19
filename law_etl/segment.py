"""segment 階段：依『編→章→節→條→項→款→目』切分中文法條。

- 章/節：中文數字（第 四 章）
- 條：阿拉伯數字，支援增訂條（第 46-1 條）
- 項：條內未編號的段落（依序給 no）
- 款：一、二、三、
- 目：（一）（二）（三）
"""

from __future__ import annotations

import re

from .chinese_num import normalize_digits

RE_CHAPTER = re.compile(r"^第\s*([一二三四五六七八九十百]+)\s*章\s*(.*)$")
RE_SECTION = re.compile(r"^第\s*([一二三四五六七八九十百]+)\s*節\s*(.*)$")
RE_ARTICLE = re.compile(r"^第\s*(\d+(?:-\d+)?)\s*條\s*(.*)$")
RE_SUBPARA = re.compile(r"^([一二三四五六七八九十]+)、\s*(.*)$")
RE_ITEM = re.compile(r"^（([一二三四五六七八九十]+)）\s*(.*)$")


def segment(body: str, part: str = "") -> list[dict]:
    articles: list[dict] = []
    chapter = ""
    section = ""
    cur: dict | None = None
    cur_para: dict | None = None
    cur_sub: dict | None = None

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        norm = normalize_digits(line)

        m = RE_CHAPTER.match(norm)
        if m:
            chapter = f"第{m.group(1)}章 {m.group(2)}".strip()
            cur = cur_para = cur_sub = None
            continue

        m = RE_SECTION.match(norm)
        if m:
            section = f"第{m.group(1)}節 {m.group(2)}".strip()
            cur = cur_para = cur_sub = None
            continue

        m = RE_ARTICLE.match(norm)
        if m:
            flno, rest = m.group(1), m.group(2).strip()
            cur = {
                "flno": flno,
                "article_label": f"第 {flno} 條",
                "part": part,
                "chapter": chapter,
                "section": section,
                "paragraphs": [],
            }
            articles.append(cur)
            cur_para = cur_sub = None
            if rest:
                cur_para = {"no": 1, "text": rest, "subparagraphs": []}
                cur["paragraphs"].append(cur_para)
            continue

        if cur is None:
            continue  # 條文開始前的前言，略過

        m = RE_ITEM.match(line)
        if m and cur_sub is not None:
            cur_sub.setdefault("items", []).append(
                {"label": f"（{m.group(1)}）", "text": m.group(2).strip()}
            )
            continue

        m = RE_SUBPARA.match(line)
        if m:
            if cur_para is None:
                cur_para = {"no": 1, "text": "", "subparagraphs": []}
                cur["paragraphs"].append(cur_para)
            cur_sub = {"label": m.group(1), "text": m.group(2).strip(), "items": []}
            cur_para["subparagraphs"].append(cur_sub)
            continue

        # 一般段落 → 新的一項
        cur_para = {"no": len(cur["paragraphs"]) + 1, "text": line, "subparagraphs": []}
        cur["paragraphs"].append(cur_para)
        cur_sub = None

    return articles
