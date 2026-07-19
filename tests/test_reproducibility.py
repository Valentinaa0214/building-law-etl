"""重跑一致性測試（驗收標準：重跑結果一致）。"""

import copy

from law_etl.pipeline import run
from law_etl import normalize as normalize_mod


def test_content_hash_stable_across_runs(tmp_path):
    import shutil, os

    # 複製 fixture 到臨時 base_dir，避免污染 data/output
    base = tmp_path
    os.makedirs(base / "data" / "fixtures")
    shutil.copy("data/fixtures/D0070115.txt", base / "data" / "fixtures" / "D0070115.txt")

    r1 = run("D0070115", base_dir=str(base))
    r2 = run("D0070115", base_dir=str(base))

    assert r1["law"]["content_hash"] == r2["law"]["content_hash"]
    assert r1["errors"] == []
    assert r1["status"] == "written"
    assert r2["status"] == "skipped"  # hash 未變 → 跳過寫入


def test_hash_independent_of_fetch_date():
    meta = {
        "law_code": "TEST",
        "law_name": "測試法",
        "competent_authority": "測試機關",
        "official_url": "https://example.com",
    }
    articles = [{
        "flno": "1", "article_label": "第 1 條", "part": "", "chapter": "第一章 X",
        "section": "", "paragraphs": [{"no": 1, "text": "內容", "subparagraphs": []}],
    }]
    law_a = normalize_mod.normalize({**meta, "fetch_date": "2026-07-19"}, copy.deepcopy(articles))
    law_b = normalize_mod.normalize({**meta, "fetch_date": "2026-08-01"}, copy.deepcopy(articles))
    assert law_a["content_hash"] == law_b["content_hash"]
