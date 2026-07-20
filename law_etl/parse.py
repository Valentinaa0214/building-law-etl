"""parse 階段：把原始內容（HTML 或純文字）轉為條文純文字。

- fixture 純文字：直接回傳
- law.moj.gov.tw LawAll 頁：依 `.law-reg-content` 結構抽出章/節/條
- 其他 HTML：通用去標籤後備
"""

from __future__ import annotations

import re


def parse_raw(raw: str) -> str:
    if _looks_like_html(raw):
        if _is_moj_law_page(raw):
            text = _parse_moj_html(raw)
            if text.strip():
                return text
        return _strip_html(raw)
    return raw


def _looks_like_html(raw: str) -> bool:
    head = raw[:2000].lower()
    return "<html" in head or "<!doctype" in head or "<div" in head


def _is_moj_law_page(raw: str) -> bool:
    head = raw[:8000].lower()
    return (
        "law.moj.gov.tw" in head
        or "law-reg-content" in head
        or 'id="pnlawfla"' in head
        or "全國法規資料庫" in raw[:8000]
    )


def _parse_moj_html(raw: str) -> str:
    """專用解析全國法規資料庫 LawAll 頁。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(raw, "html.parser")
    root = soup.select_one("#pnLawFla .law-reg-content") or soup.select_one(
        ".law-reg-content"
    )
    if root is None:
        return ""

    lines: list[str] = []
    for el in root.find_all(recursive=False):
        classes = el.get("class") or []
        if "h3" in classes:
            title = _norm_space(el.get_text(" ", strip=True))
            if title:
                lines.append(title)
            continue
        if "row" not in classes:
            continue
        art_lines = _row_to_lines(el)
        if art_lines:
            lines.extend(art_lines)

    return "\n".join(lines)


def _row_to_lines(row) -> list[str]:
    link = row.select_one(".col-no a[href*='flno=']")
    if link is None:
        return []
    label = _norm_space(link.get_text(" ", strip=True))
    if not label:
        return []

    out = [label]
    article = row.select_one(".law-article")
    if article is None:
        return out

    for child in article.find_all(recursive=False):
        classes = child.get("class") or []
        text = _norm_space(child.get_text(" ", strip=True))
        if not text:
            continue
        if "text-pre" in classes:
            # 表格併入上一行（通常是「一、…依其規定：」），避免被切成新項
            if len(out) > 1:
                out[-1] = f"{out[-1]} {text}"
            else:
                out.append(text)
        else:
            out.append(text)
    return out


def _norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_html(raw: str) -> str:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text("\n")
    except Exception:
        text = re.sub(r"<[^>]+>", "\n", raw)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)
