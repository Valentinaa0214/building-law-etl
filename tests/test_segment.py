"""條文切分正確性測試（對齊 §90/91/92/93/95 fixture）。"""

from law_etl.segment import segment
from law_etl.chinese_num import cn_to_int

FIXTURE = open("data/fixtures/D0070115.txt", encoding="utf-8").read()


def _by_flno(articles):
    return {a["flno"]: a for a in articles}


def test_article_count_and_flno():
    arts = _by_flno(segment(FIXTURE, part="建築設計施工編"))
    assert set(arts) == {"90", "91", "92", "93", "95"}


def test_hierarchy_context():
    arts = _by_flno(segment(FIXTURE, part="建築設計施工編"))
    a92 = arts["92"]
    assert a92["part"] == "建築設計施工編"
    assert a92["chapter"].startswith("第四章")
    assert a92["section"].startswith("第一節")


def test_subparagraphs():
    arts = _by_flno(segment(FIXTURE, part="建築設計施工編"))
    # §92：款一、款二
    subs = arts["92"]["paragraphs"][0]["subparagraphs"]
    assert [s["label"] for s in subs] == ["一", "二"]


def test_items_under_subparagraph():
    arts = _by_flno(segment(FIXTURE, part="建築設計施工編"))
    # §93 款二底下有（一）（二）（三）三目
    sub2 = arts["93"]["paragraphs"][0]["subparagraphs"][1]
    assert sub2["label"] == "二"
    assert [it["label"] for it in sub2["items"]] == ["（一）", "（二）", "（三）"]


def test_amended_article_flno_regex():
    arts = _by_flno(segment("第 46-1 條\n測試條文。", part=""))
    assert "46-1" in arts


def test_cn_to_int():
    assert cn_to_int("四") == 4
    assert cn_to_int("十五") == 15
    assert cn_to_int("二十") == 20
