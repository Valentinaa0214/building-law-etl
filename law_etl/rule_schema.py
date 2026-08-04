"""Rule Spec v0：載入 JSON Schema 與欄位驗證。"""

from __future__ import annotations

import json
import os
from typing import Any

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "schemas",
    "rule_spec_v0.json",
)

_REQUIRED = [
    "rule_id",
    "law_code",
    "law_name",
    "article",
    "version",
    "extractable",
    "review_status",
    "confidence",
    "source_quote",
]


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_rule(rule: dict[str, Any]) -> list[dict]:
    """輕量欄位驗證（不強制依賴 jsonschema 套件）。回傳錯誤清單。"""
    errors: list[dict] = []

    for key in _REQUIRED:
        if key not in rule or rule[key] is None or rule[key] == "":
            errors.append({"field": key, "issue": "missing"})

    status = rule.get("review_status")
    if status not in {"draft", "review_required", "reviewed", "active", "rejected"}:
        errors.append({"field": "review_status", "issue": "invalid_enum", "value": status})

    conf = rule.get("confidence")
    if not isinstance(conf, (int, float)) or not (0 <= float(conf) <= 1):
        errors.append({"field": "confidence", "issue": "out_of_range", "value": conf})

    if rule.get("extractable") is True:
        for key in ("target", "operator", "threshold", "unit"):
            if rule.get(key) is None or rule.get(key) == "":
                errors.append({"field": key, "issue": "required_when_extractable"})

    uncertain = rule.get("uncertain_fields") or []
    if uncertain and status != "review_required":
        errors.append(
            {
                "field": "review_status",
                "issue": "must_be_review_required_when_uncertain",
                "uncertain_fields": uncertain,
            }
        )

    return errors


def validate_rules(rules: list[dict]) -> list[dict]:
    out: list[dict] = []
    for i, rule in enumerate(rules):
        for err in validate_rule(rule):
            out.append({"index": i, "rule_id": rule.get("rule_id"), **err})
    return out
