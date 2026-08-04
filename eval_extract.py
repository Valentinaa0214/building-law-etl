#!/usr/bin/env python3
"""評測：抽取結果 vs gold 標註（欄位 exact match + review_status 約束）。"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict


CORE_FIELDS = ["extractable", "target", "operator", "threshold", "unit", "review_status"]


def _index_by_article(rules: list[dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = defaultdict(list)
    for r in rules:
        idx[str(r.get("article"))].append(r)
    return idx


def _best_match(gold: dict, cands: list[dict]) -> dict | None:
    if not cands:
        return None
    # 優先同 target；否則第一筆
    for c in cands:
        if gold.get("target") and c.get("target") == gold.get("target"):
            return c
    return cands[0]


def evaluate(pred_rules: list[dict], gold_rules: list[dict]) -> dict:
    by_art = _index_by_article(pred_rules)
    field_hits = {f: 0 for f in CORE_FIELDS}
    field_total = {f: 0 for f in CORE_FIELDS}
    article_ok = 0
    rows = []

    for g in gold_rules:
        art = str(g["article"])
        pred = _best_match(g, by_art.get(art, []))
        row = {"article": art, "gold_rule_id": g.get("rule_id"), "matched": pred is not None}
        if pred is None:
            rows.append(row)
            continue
        all_ok = True
        for f in CORE_FIELDS:
            # gold 若省略某欄，不計入
            if f not in g:
                continue
            field_total[f] += 1
            gv, pv = g.get(f), pred.get(f)
            # threshold 數值容差
            ok = gv == pv
            if f == "threshold" and isinstance(gv, (int, float)) and isinstance(pv, (int, float)):
                ok = abs(float(gv) - float(pv)) < 1e-6
            if ok:
                field_hits[f] += 1
            else:
                all_ok = False
            row[f] = {"gold": gv, "pred": pv, "ok": ok}
        if all_ok:
            article_ok += 1
        rows.append(row)

    n = len(gold_rules) or 1
    field_acc = {
        f: (field_hits[f] / field_total[f] if field_total[f] else None) for f in CORE_FIELDS
    }
    return {
        "gold_count": len(gold_rules),
        "pred_count": len(pred_rules),
        "article_exact_match": article_ok / n,
        "field_accuracy": field_acc,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pred", required=True, help="extract_rules 輸出 JSON")
    p.add_argument("--gold", required=True, help="gold 標註 JSON")
    p.add_argument("--out", default="")
    args = p.parse_args(argv)

    with open(args.pred, encoding="utf-8") as f:
        pred = json.load(f)
    with open(args.gold, encoding="utf-8") as f:
        gold = json.load(f)

    pred_rules = pred["rules"] if isinstance(pred, dict) and "rules" in pred else pred
    gold_rules = gold["rules"] if isinstance(gold, dict) and "rules" in gold else gold

    report = evaluate(pred_rules, gold_rules)
    summary = {
        "gold_count": report["gold_count"],
        "pred_count": report["pred_count"],
        "article_exact_match": round(report["article_exact_match"], 3),
        "field_accuracy": {
            k: (round(v, 3) if v is not None else None)
            for k, v in report["field_accuracy"].items()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
