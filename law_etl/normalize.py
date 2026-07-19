"""normalize 階段：套用 schema、計算 hash、補來源 URL 與版本欄位。

hash 只依條文內容（不含 fetch_date），確保重跑一致、可做版本 diff。
"""

from __future__ import annotations

import hashlib

from .config import LAW_SINGLE_URL


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _article_blob(article: dict) -> str:
    parts = [article["flno"]]
    for para in article["paragraphs"]:
        parts.append(para["text"])
        for sub in para.get("subparagraphs", []):
            parts.append(f'{sub["label"]}、{sub["text"]}')
            for item in sub.get("items", []):
                parts.append(f'{item["label"]}{item["text"]}')
    return "\n".join(parts)


def normalize(meta: dict, articles: list[dict]) -> dict:
    norm_articles = []
    for a in articles:
        a2 = dict(a)
        a2["article_hash"] = _sha(_article_blob(a))
        a2["source_url"] = LAW_SINGLE_URL.format(flno=a["flno"], pcode=meta["law_code"])
        a2["review_status"] = "draft"
        norm_articles.append(a2)

    content_hash = _sha("|".join(a["article_hash"] for a in norm_articles))

    return {
        "law_code": meta["law_code"],
        "law_name": meta["law_name"],
        "competent_authority": meta["competent_authority"],
        "official_url": meta["official_url"],
        "publish_date": meta.get("publish_date"),
        "amend_date": meta.get("amend_date"),
        "effective_status": meta.get("effective_status", "in_force"),
        "fetch_date": meta["fetch_date"],
        "content_hash": content_hash,
        "articles": norm_articles,
    }
