"""fetch 階段：取得法規原始內容。

來源優先序（皆可離線重跑）：
1. data/fixtures/{law_code}.txt （已版控的測試樣本，離線可用）
2. data/raw/{law_code}.html      （HTTP 抓取快取）
3. 線上抓取 law.moj.gov.tw       （--refresh 或無快取時）
"""

from __future__ import annotations

import datetime
import os

_UA = "building-law-etl/0.1 (research; contact: 富品盃 team)"


def fetch_raw(cfg: dict, base_dir: str = ".", refresh: bool = False) -> tuple[str, str]:
    """回傳 (raw_text, fetch_date)。"""
    law_code = cfg["law_code"]
    fixture = os.path.join(base_dir, "data", "fixtures", f"{law_code}.txt")
    cache = os.path.join(base_dir, "data", "raw", f"{law_code}.html")

    if not refresh and os.path.exists(fixture):
        with open(fixture, encoding="utf-8") as f:
            return f.read(), _today()
    if not refresh and os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return f.read(), _today()

    html = _http_get(cfg["official_url"])
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        f.write(html)
    return html, _today()


def _http_get(url: str) -> str:
    import requests

    resp = requests.get(url, headers={"User-Agent": _UA}, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _today() -> str:
    return datetime.date.today().isoformat()
