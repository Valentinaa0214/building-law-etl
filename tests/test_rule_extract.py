"""Rule Spec 抽取 / 驗證 / 覆核格式測試。"""

from __future__ import annotations

import json

from law_etl.rule_extract import (
    extract_article,
    extract_heuristic,
    article_plain_text,
    normalize_llm_rules,
)
from law_etl.rule_schema import validate_rule, validate_rules
from law_etl.review import rules_to_review_rows, apply_review_decisions


def _mini_law():
    return {
        "law_code": "D0070115",
        "law_name": "建築技術規則建築設計施工編",
        "amend_date": "2026-02-23",
    }


def test_validate_extractable_requires_fields():
    bad = {
        "rule_id": "BTR-TEST-X-001",
        "law_code": "D0070115",
        "law_name": "x",
        "article": "90",
        "version": "2026-02-23",
        "extractable": True,
        "review_status": "draft",
        "confidence": 0.9,
        "source_quote": "寬度不得小於一‧二公尺",
        # missing target/operator/threshold/unit
    }
    errs = validate_rule(bad)
    assert any(e["issue"] == "required_when_extractable" for e in errs)


def test_uncertain_forces_review_required():
    rule = {
        "rule_id": "BTR-TEST-X-002",
        "law_code": "D0070115",
        "law_name": "x",
        "article": "92",
        "version": "2026-02-23",
        "extractable": False,
        "review_status": "draft",
        "confidence": 0.4,
        "source_quote": "走廊寬度依其規定",
        "uncertain_fields": ["threshold"],
    }
    errs = validate_rule(rule)
    assert any(e["issue"] == "must_be_review_required_when_uncertain" for e in errs)


def test_heuristic_exit_width():
    law = _mini_law()
    article = {
        "flno": "90",
        "chapter": "第四章",
        "section": "第一節",
        "paragraphs": [
            {
                "no": 1,
                "text": "直通樓梯於避難層開向屋外之出入口，應依左列規定：",
                "subparagraphs": [
                    {
                        "label": "二",
                        "text": "直通樓梯於避難層開向屋外之出入口，寬度不得小於一‧二公尺，高度不得小於一‧八公尺。",
                        "items": [],
                    }
                ],
            }
        ],
    }
    rules = extract_heuristic(law, article)
    assert validate_rules(rules) == []
    widths = [r for r in rules if r["target"] == "exit.width_mm"]
    heights = [r for r in rules if r["target"] == "exit.height_mm"]
    assert widths and widths[0]["threshold"] == 1200 and widths[0]["operator"] == ">="
    assert heights and heights[0]["threshold"] == 1800


def test_deleted_article_review_required():
    law = _mini_law()
    article = {
        "flno": "103",
        "chapter": "第四章",
        "section": "",
        "paragraphs": [{"no": 1, "text": "（刪除）", "subparagraphs": []}],
    }
    rules = extract_article(law, article)
    assert len(rules) == 1
    assert rules[0]["extractable"] is False
    assert rules[0]["review_status"] == "review_required"


def test_review_sheet_and_apply():
    rules = [
        {
            "rule_id": "BTR-EVAC-EXIT-WIDTH-001-90",
            "article": "90",
            "extractable": True,
            "target": "exit.width_mm",
            "operator": ">=",
            "threshold": 1200,
            "unit": "mm",
            "confidence": 0.9,
            "review_status": "draft",
            "uncertain_fields": [],
            "source_quote": "寬度不得小於一‧二公尺",
            "notes": None,
        }
    ]
    rows = rules_to_review_rows(rules)
    assert rows[0]["reviewer_decision"] == ""
    rows[0]["reviewer_decision"] = "approve"
    updated = apply_review_decisions(rules, rows)
    assert updated[0]["review_status"] == "reviewed"


def test_gold_has_at_least_20():
    with open("data/gold/rule_extract_gold_v0.json", encoding="utf-8") as f:
        gold = json.load(f)
    assert len(gold["rules"]) >= 20
    arts = {r["article"] for r in gold["rules"]}
    assert len(arts) >= 20


def test_mvp_active_bundle():
    with open("data/mvp/mvp_rules_active_v0.json", encoding="utf-8") as f:
        bundle = json.load(f)
    rules = bundle["rules"]
    assert bundle["rule_count"] == len(rules) == 11
    assert validate_rules(rules) == []
    assert all(r["review_status"] == "active" for r in rules)
    targets = {r["target"] for r in rules}
    assert "exit.width_mm" in targets
    assert "corridor.width_mm" in targets
    assert "evac.walking_distance_m" in targets


def test_normalize_llm_rules_forces_article_and_unit():
    law = _mini_law()
    article = {"flno": "92", "chapter": "第四章", "section": "", "paragraphs": []}
    raw = [
        {
            "rule_id": "BTR-EVAC-STAIR-COUNT-001",
            "law_code": "D0070115",
            "law_name": "建築技術規則建築設計施工編",
            "article": "90",
            "version": "2026-02-23",
            "extractable": True,
            "target": "stair.count",
            "operator": ">=",
            "threshold": 2,
            "unit": None,
            "review_status": "draft",
            "confidence": 0.9,
            "source_quote": "二座以上之直通樓梯",
            "uncertain_fields": ["unit"],
        },
        {
            "rule_id": "BTR-REF-RULE",
            "law_code": "D0070115",
            "law_name": "建築技術規則建築設計施工編",
            "article": "90",
            "version": "2026-02-23",
            "extractable": True,
            "target": "evac.walking_distance_m",
            "operator": "<=",
            "threshold": None,
            "unit": None,
            "review_status": "draft",
            "confidence": 0.7,
            "source_quote": "不得大於第九十三條規定",
            "uncertain_fields": [],
        },
    ]
    fixed = normalize_llm_rules(law, article, raw)
    assert fixed[0]["article"] == "92"
    assert fixed[0]["unit"] == "count"
    assert fixed[0]["rule_id"].endswith("-92")
    assert "unit" not in (fixed[0].get("uncertain_fields") or [])
    assert fixed[1]["extractable"] is False
    assert fixed[1]["review_status"] == "review_required"
    assert validate_rules(fixed) == []
