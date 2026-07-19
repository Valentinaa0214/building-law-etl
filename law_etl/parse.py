"""parse 階段：把原始內容（HTML 或純文字）轉為條文純文字。

fixture 為純文字，直接回傳；線上來源為 HTML，去除標籤後回傳。
"""

from __future__ import annotations

import re


def parse_raw(raw: str) -> str:
    if _looks_like_html(raw):
        return _strip_html(raw)
    return raw


def _looks_like_html(raw: str) -> bool:
    head = raw[:2000].lower()
    return "<html" in head or "<!doctype" in head or "<div" in head


def _strip_html(raw: str) -> str:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text("\n")
    except Exception:
        text = re.sub(r"<[^>]+>", "\n", raw)
    # 壓縮多餘空行
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)
