#!/usr/bin/env python3
"""條文結構化抽取 CLI。

用法：
  python extract_rules.py --law-json data/output/D0070115.json --chapter-prefix 第四章
  python extract_rules.py --law-json data/output/D0070115.json --flnos 90,91,92,93,95
  python extract_rules.py --law-json data/output/D0070115.json --provider openai
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from law_etl.rule_extract import extract_law
from law_etl.rule_schema import validate_rules
from law_etl.review import write_review_sheet


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LLM/heuristic 條文→Rule Spec v0 抽取")
    p.add_argument("--law-json", required=True, help="ETL 輸出的 normalized law JSON")
    p.add_argument("--flnos", default="", help="逗號分隔 flno；空則全部（可搭配 chapter）")
    p.add_argument("--chapter-prefix", default="", help="只抽 chapter 以此開頭的條文")
    p.add_argument("--provider", default="heuristic", choices=["heuristic", "openai"])
    p.add_argument("--out-dir", default="data/output/rules")
    args = p.parse_args(argv)

    with open(args.law_json, encoding="utf-8") as f:
        law = json.load(f)

    flnos = [x.strip() for x in args.flnos.split(",") if x.strip()] or None

    def chapter_filter(article: dict) -> bool:
        if not args.chapter_prefix:
            return True
        return (article.get("chapter") or "").startswith(args.chapter_prefix)

    result = extract_law(
        law,
        flnos=flnos,
        provider=args.provider,
        article_filter=chapter_filter if args.chapter_prefix else None,
    )

    errors = validate_rules(result["rules"])
    result["validation_errors"] = errors
    result["validation_ok"] = len(errors) == 0

    os.makedirs(args.out_dir, exist_ok=True)
    stem = f"{law['law_code']}_{args.provider}"
    out_json = os.path.join(args.out_dir, f"{stem}_rules.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    paths = write_review_sheet(result["rules"], args.out_dir, stem=f"{stem}_review")

    review_required = sum(1 for r in result["rules"] if r.get("review_status") == "review_required")
    extractable = sum(1 for r in result["rules"] if r.get("extractable"))
    print(
        f"articles={result['article_count']} rules={result['rule_count']} "
        f"extractable={extractable} review_required={review_required} "
        f"validation_errors={len(errors)}"
    )
    print(f"rules -> {out_json}")
    print(f"review sheet -> {paths['csv']}")
    return 0 if result["validation_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
