"""validate 階段：欄位與層級檢核；不合格標為 review_required。"""

from __future__ import annotations

_REQUIRED_ARTICLE_FIELDS = ["flno", "chapter", "source_url", "article_hash"]


def validate(law: dict) -> list[dict]:
    """回傳錯誤清單（空 list 代表通過）。"""
    errors: list[dict] = []

    if not law.get("articles"):
        errors.append({"issue": "no_articles", "review_required": True})
        return errors

    seen: set[str] = set()
    for a in law["articles"]:
        flno = a.get("flno")
        for field in _REQUIRED_ARTICLE_FIELDS:
            if not a.get(field):
                errors.append({"flno": flno, "field": field, "issue": "missing"})
        if not a.get("paragraphs"):
            errors.append({"flno": flno, "issue": "empty_article", "review_required": True})
        if flno in seen:
            errors.append({"flno": flno, "issue": "duplicate_flno"})
        seen.add(flno)

    return errors
