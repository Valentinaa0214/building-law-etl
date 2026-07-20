"""真實 law.moj.gov.tw HTML 解析測試。"""

from law_etl.parse import parse_raw
from law_etl.segment import segment

SAMPLE = open("data/fixtures/D0070115_moj_sample.html", encoding="utf-8").read()


def test_moj_html_emits_article_markers():
    text = parse_raw(SAMPLE)
    assert "第 四 章" in text or "第四章" in text.replace(" ", "")
    assert "第 92 條" in text
    assert "走廊之設置應依左列規定" in text


def test_moj_html_segments_mvp_articles():
    arts = {a["flno"]: a for a in segment(parse_raw(SAMPLE), part="建築設計施工編")}
    assert set(arts) == {"90", "91", "92", "93"}
    assert arts["92"]["chapter"].startswith("第四章")
    assert arts["92"]["section"].startswith("第一節")
    labels = [s["label"] for s in arts["92"]["paragraphs"][0]["subparagraphs"] ]
    assert labels == ["一", "二", "三", "四"]


def test_plain_fixture_still_passthrough():
    raw = open("data/fixtures/D0070115.txt", encoding="utf-8").read()
    assert parse_raw(raw) == raw
