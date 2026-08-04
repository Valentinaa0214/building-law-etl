"""人工覆核格式：由抽取結果產生 review sheet（JSON + CSV）。"""

from __future__ import annotations

import csv
import json
import os
from typing import Any


REVIEW_COLUMNS = [
    "rule_id",
    "article",
    "extractable",
    "target",
    "operator",
    "threshold",
    "unit",
    "confidence",
    "review_status",
    "uncertain_fields",
    "source_quote",
    "notes",
    # 人工欄位
    "reviewer_decision",  # approve | revise | reject
    "reviewer_corrected_threshold",
    "reviewer_corrected_target",
    "reviewer_comment",
    "reviewer_name",
    "reviewed_at",
]


def rules_to_review_rows(rules: list[dict]) -> list[dict[str, Any]]:
    rows = []
    for r in rules:
        rows.append(
            {
                "rule_id": r.get("rule_id"),
                "article": r.get("article"),
                "extractable": r.get("extractable"),
                "target": r.get("target"),
                "operator": r.get("operator"),
                "threshold": r.get("threshold"),
                "unit": r.get("unit"),
                "confidence": r.get("confidence"),
                "review_status": r.get("review_status"),
                "uncertain_fields": "|".join(r.get("uncertain_fields") or []),
                "source_quote": r.get("source_quote"),
                "notes": r.get("notes"),
                "reviewer_decision": "",
                "reviewer_corrected_threshold": "",
                "reviewer_corrected_target": "",
                "reviewer_comment": "",
                "reviewer_name": "",
                "reviewed_at": "",
            }
        )
    return rows


def write_review_sheet(rules: list[dict], out_dir: str, stem: str = "review_sheet") -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    rows = rules_to_review_rows(rules)
    json_path = os.path.join(out_dir, f"{stem}.json")
    csv_path = os.path.join(out_dir, f"{stem}.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "description": "人工覆核表：填 reviewer_decision=approve|revise|reject；revise 時填 corrected 欄位",
                "workflow": "draft/review_required → reviewed → active",
                "rows": rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return {"json": json_path, "csv": csv_path}


def apply_review_decisions(rules: list[dict], review_rows: list[dict]) -> list[dict]:
    """依覆核表更新 review_status（approve→reviewed；reject→rejected；revise→reviewed 並套用修正）。"""
    by_id = {r["rule_id"]: dict(r) for r in rules}
    for row in review_rows:
        rid = row.get("rule_id")
        if rid not in by_id:
            continue
        decision = (row.get("reviewer_decision") or "").strip().lower()
        rule = by_id[rid]
        if decision == "approve":
            rule["review_status"] = "reviewed"
            rule["uncertain_fields"] = []
        elif decision == "reject":
            rule["review_status"] = "rejected"
        elif decision == "revise":
            if row.get("reviewer_corrected_threshold") not in (None, ""):
                rule["threshold"] = float(row["reviewer_corrected_threshold"])
            if row.get("reviewer_corrected_target"):
                rule["target"] = row["reviewer_corrected_target"]
            rule["review_status"] = "reviewed"
            rule["uncertain_fields"] = []
            comment = row.get("reviewer_comment") or ""
            rule["notes"] = ((rule.get("notes") or "") + f"; reviewed:{comment}").strip("; ")
        by_id[rid] = rule
    return list(by_id.values())
