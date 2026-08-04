"""條文 → Rule Spec v0 結構化抽取。

providers:
- heuristic：離線規則式 baseline（預設，可重現、可測）
- openai：可選 LLM（需 OPENAI_API_KEY）；失敗時回退 heuristic 並標 review_required
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable

from .chinese_num import normalize_digits
from .rule_schema import validate_rule

PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "prompts",
    "extract_rule_spec.md",
)

# 一‧二公尺 / 1.2公尺 / 三十公尺
_RE_LENGTH = re.compile(
    r"(不得小於|不得超過|不得大於|以上|以下|超過|未滿|小於)"
    r".{0,6}?"
    r"([一二三四五六七八九十百零〇○\.‧・\d]+)\s*(公尺|公分|米)"
)
_RE_COUNT = re.compile(r"(二座以上|一座以上|二處以上|一處以上)")
_RE_DELETED = re.compile(r"^（刪除）$|本條刪除")
_CN_MAP = {
    "零": 0, "〇": 0, "○": 0,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}


def article_plain_text(article: dict) -> str:
    parts: list[str] = []
    for para in article.get("paragraphs", []):
        if para.get("text"):
            parts.append(para["text"])
        for sub in para.get("subparagraphs", []):
            parts.append(f'{sub.get("label", "")}、{sub.get("text", "")}')
            for item in sub.get("items", []):
                parts.append(f'{item.get("label", "")}{item.get("text", "")}')
    return "\n".join(parts)


def load_prompt_template() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def render_prompt(law: dict, article: dict) -> str:
    tmpl = load_prompt_template()
    return (
        tmpl.replace("{{law_code}}", law["law_code"])
        .replace("{{law_name}}", law["law_name"])
        .replace("{{version}}", str(law.get("amend_date") or ""))
        .replace("{{flno}}", article["flno"])
        .replace("{{chapter}}", article.get("chapter") or "")
        .replace("{{section}}", article.get("section") or "")
        .replace("{{article_text}}", article_plain_text(article))
    )


def _parse_cn_decimal(raw: str) -> float | None:
    s = normalize_digits(raw).replace("・", ".").replace("‧", ".").replace("·", ".")
    s = s.replace("○", "0").replace("〇", "0")
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    # 三十 / 五十 / 十五
    if "十" in s and all(ch in "一二三四五六七八九十" for ch in s):
        from .chinese_num import cn_to_int

        v = cn_to_int(s)
        return float(v) if v is not None else None
    # 一‧二 → 已轉成 1.2；全中文小數少見，略
    digits = []
    for ch in s:
        if ch.isdigit() or ch == ".":
            digits.append(ch)
        elif ch in _CN_MAP:
            digits.append(str(_CN_MAP[ch]))
    joined = "".join(digits)
    if joined and re.fullmatch(r"\d+(\.\d+)?", joined):
        return float(joined)
    return None


def _op_from_phrase(phrase: str) -> str:
    if "不得小於" in phrase or phrase.endswith("以上") or "以上" in phrase:
        return ">="
    if "不得超過" in phrase or "不得大於" in phrase or "以下" in phrase:
        return "<="
    if "超過" in phrase:
        return ">"
    if "未滿" in phrase or "小於" in phrase:
        return "<"
    return ">="


def _guess_target(context: str) -> str | None:
    """依門檻前方局部用語判斷 target（避免同一句後段的『高度』汙染前段『寬度』）。"""
    # 只取數字門檻前方片段，避免後續條款污染
    head = context
    if "步行距離" in head or "步行路徑" in head:
        return "evac.walking_distance_m"
    if "排煙口" in head and "距離" in head:
        return "smoke.horizontal_distance_m"
    # 寬/高：以最靠近門檻的關鍵字為準
    width_pos = max(head.rfind("寬度"), head.rfind("總寬度"), head.rfind("寬"))
    height_pos = max(head.rfind("高度"), head.rfind("高"))
    if width_pos >= 0 or height_pos >= 0:
        use_height = height_pos > width_pos
        if "走廊" in head:
            return "corridor.width_mm" if not use_height else "corridor.width_mm"
        if "出入口" in head or "開口" in head:
            return "exit.height_mm" if use_height else "exit.width_mm"
        if "樓梯" in head:
            return "stair.width_mm"
        return "geometry.height_mm" if use_height else "geometry.width_mm"
    return None


def _base_rule(law: dict, article: dict, **kwargs) -> dict:
    rule = {
        "rule_id": kwargs.get("rule_id") or f"BTR-DRAFT-{article['flno']}-001",
        "law_code": law["law_code"],
        "law_name": law["law_name"],
        "article": article["flno"],
        "article_ref": kwargs.get("article_ref"),
        "version": law.get("amend_date"),
        "extractable": kwargs.get("extractable", False),
        "scope": kwargs.get("scope") or {"building_use": [], "conditions": []},
        "target": kwargs.get("target"),
        "operator": kwargs.get("operator"),
        "threshold": kwargs.get("threshold"),
        "unit": kwargs.get("unit"),
        "severity": kwargs.get("severity", "high"),
        "exceptions": kwargs.get("exceptions") or [],
        "evidence_required": kwargs.get("evidence_required") or [],
        "source_quote": kwargs.get("source_quote") or article_plain_text(article)[:200],
        "confidence": kwargs.get("confidence", 0.0),
        "uncertain_fields": kwargs.get("uncertain_fields") or [],
        "review_status": kwargs.get("review_status", "draft"),
        "notes": kwargs.get("notes"),
    }
    if rule["uncertain_fields"] and rule["review_status"] == "draft":
        rule["review_status"] = "review_required"
    return rule


def extract_heuristic(law: dict, article: dict) -> list[dict]:
    text = article_plain_text(article)
    flno = article["flno"]

    if _RE_DELETED.search(text.strip()) or text.strip() == "（刪除）":
        return [
            _base_rule(
                law,
                article,
                rule_id=f"BTR-META-DELETED-{flno}",
                extractable=False,
                confidence=1.0,
                review_status="review_required",
                source_quote=text.strip() or "（刪除）",
                notes="刪除條文，不產生可執行規則",
                uncertain_fields=["extractable"],
            )
        ]

    rules: list[dict] = []
    # 掃描長度門檻
    for m in _RE_LENGTH.finditer(text):
        phrase, raw_num, unit_zh = m.group(1), m.group(2), m.group(3)
        value = _parse_cn_decimal(raw_num)
        if value is None:
            continue
        if unit_zh in {"公尺", "米"}:
            # 僅取門檻前方上下文，避免下一款的『高度』汙染『寬度』
            start = max(0, m.start() - 40)
            ctx = text[start:m.start()]
            # 遠一點的語境（跨款標題）
            far = text[max(0, m.start() - 120) : m.start()]
            target = _guess_target(ctx)
            if target is None and ("步行距離" in far or "步行路徑" in far):
                target = "evac.walking_distance_m"
            if target is None and value >= 10 and "寬" not in ctx and "高" not in ctx:
                # 大數值公尺且無寬高線索 → 傾向距離
                target = "evac.walking_distance_m"
            if target and target.endswith("_m"):
                unit, threshold = "m", value
            else:
                unit, threshold = "mm", value * 1000
                if not target:
                    target = "geometry.width_mm"
        else:  # 公分
            unit, threshold = "mm", value * 10
            ctx = text[max(0, m.start() - 40) : m.start()]
            target = _guess_target(ctx) or "geometry.width_mm"

        uncertain: list[str] = []
        status = "draft"
        conf = 0.85
        # 表格／左表 → 不確定
        if "左表" in text or "┌" in text or "依其規定" in text:
            uncertain.append("threshold")
            uncertain.append("scope.building_use")
            status = "review_required"
            conf = 0.45
        # 計算值公式
        if "計算值" in text or "每" in m.group(0) and "平方公尺" in text[max(0, m.start() - 40) : m.end()]:
            if "計算值" in text:
                uncertain.append("threshold")
                status = "review_required"
                conf = min(conf, 0.5)

        domain = "EVAC"
        topic = {
            "exit.width_mm": "EXIT-WIDTH",
            "exit.height_mm": "EXIT-HEIGHT",
            "corridor.width_mm": "CORRIDOR-WIDTH",
            "evac.walking_distance_m": "WALK-DIST",
            "stair.width_mm": "STAIR-WIDTH",
        }.get(target or "", "METRIC")
        n = len(rules) + 1
        rules.append(
            _base_rule(
                law,
                article,
                rule_id=f"BTR-{domain}-{topic}-{n:03d}-{flno}",
                extractable=True,
                target=target,
                operator=_op_from_phrase(phrase),
                threshold=threshold,
                unit=unit,
                source_quote=m.group(0),
                confidence=conf,
                uncertain_fields=uncertain,
                review_status=status,
                evidence_required=["geometry", "building_use"],
                scope={"building_use": [], "conditions": []},
            )
        )

    # 二座以上 → count
    if _RE_COUNT.search(text) and "直通樓梯" in text:
        rules.append(
            _base_rule(
                law,
                article,
                rule_id=f"BTR-EVAC-STAIR-COUNT-001-{flno}",
                extractable=True,
                target="stair.count",
                operator=">=",
                threshold=2,
                unit="count",
                source_quote="應自各該層設置二座以上之直通樓梯" if "二座以上" in text else "一座以上之直通樓梯",
                confidence=0.7,
                uncertain_fields=["scope.conditions"],
                review_status="review_required",
                evidence_required=["stair_graph"],
            )
        )

    if not rules:
        return [
            _base_rule(
                law,
                article,
                rule_id=f"BTR-META-NONEXEC-{flno}",
                extractable=False,
                confidence=0.3,
                review_status="review_required",
                source_quote=text[:240],
                notes="未抽到單一數值門檻（可能為定義、程序、表格或多條件）",
                uncertain_fields=["target", "threshold"],
            )
        ]

    # 去重（同 target+threshold+op）
    seen = set()
    uniq = []
    for r in rules:
        key = (r["target"], r["operator"], r["threshold"], r["unit"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def _infer_unit_from_target(target: str | None) -> str | None:
    if not target:
        return None
    if target.endswith(".count"):
        return "count"
    if ".slope" in target:
        return "ratio"
    if target.endswith("_sqm") or ".area_sqm" in target:
        return "sqm"
    if target.endswith("_mm"):
        return "mm"
    if target.endswith("_m"):
        return "m"
    if target.endswith("_cm"):
        return "cm"
    return None


def normalize_llm_rules(law: dict, article: dict, rules: list[dict]) -> list[dict]:
    """OpenAI 輸出後處理：強制 article、補 law 欄位、推斷 unit、修正不可抽取規則。"""
    flno = article["flno"]
    normalized: list[dict] = []

    for i, raw in enumerate(rules):
        rule = dict(raw)
        rule["article"] = flno
        rule.setdefault("law_code", law["law_code"])
        rule.setdefault("law_name", law["law_name"])
        rule.setdefault("version", law.get("amend_date"))
        if not rule.get("severity"):
            rule["severity"] = "high"
        rule.setdefault("scope", {"building_use": [], "conditions": []})
        rule.setdefault("exceptions", [])
        rule.setdefault("evidence_required", [])

        if rule.get("extractable") and rule.get("target") and not rule.get("unit"):
            inferred = _infer_unit_from_target(rule["target"])
            if inferred:
                rule["unit"] = inferred
                uncertain = [f for f in (rule.get("uncertain_fields") or []) if f != "unit"]
                rule["uncertain_fields"] = uncertain

        if rule.get("extractable") and rule.get("threshold") is None:
            rule["extractable"] = False
            rule["review_status"] = "review_required"
            uncertain = list(rule.get("uncertain_fields") or [])
            for field in ("threshold", "unit"):
                if field not in uncertain:
                    uncertain.append(field)
            rule["uncertain_fields"] = uncertain
            note = rule.get("notes") or ""
            rule["notes"] = (note + "; auto:missing_threshold→non_extractable").strip("; ")

        base_rid = rule.get("rule_id") or f"BTR-LLM-{i + 1:03d}"
        rule["rule_id"] = f"{base_rid}-{flno}"

        if rule.get("uncertain_fields") and rule.get("review_status") == "draft":
            rule["review_status"] = "review_required"

        normalized.append(rule)
    return normalized


def extract_openai(law: dict, article: dict) -> list[dict]:
    """呼叫 OpenAI Chat Completions；失敗則丟例外由上層處理。"""
    import urllib.request

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = render_prompt(law, article)
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Return a JSON object with key `rules` whose value is an array of Rule Spec v0 objects.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    data = json.loads(content)
    rules = data if isinstance(data, list) else data.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("LLM output is not a rules list")
    return rules


def extract_article(
    law: dict,
    article: dict,
    provider: str = "heuristic",
) -> list[dict]:
    """抽取單一條文，並做欄位驗證；驗證失敗標 review_required。"""
    if provider == "openai":
        try:
            rules = normalize_llm_rules(law, article, extract_openai(law, article))
        except Exception as exc:  # noqa: BLE001 — 回退 baseline
            rules = extract_heuristic(law, article)
            for r in rules:
                r["notes"] = f"openai_failed:{exc}; fallback=heuristic"
                r["review_status"] = "review_required"
                if "provider" not in (r.get("uncertain_fields") or []):
                    r.setdefault("uncertain_fields", []).append("provider")
    else:
        rules = extract_heuristic(law, article)

    fixed: list[dict] = []
    for r in rules:
        errs = validate_rule(r)
        if errs:
            r["review_status"] = "review_required"
            fields = r.get("uncertain_fields") or []
            for e in errs:
                f = e.get("field")
                if f and f not in fields:
                    fields.append(f)
            r["uncertain_fields"] = fields
            note = r.get("notes") or ""
            r["notes"] = (note + f"; validate_errors={errs}").strip("; ")
        fixed.append(r)
    return fixed


def extract_law(
    law: dict,
    *,
    flnos: list[str] | None = None,
    provider: str = "heuristic",
    article_filter: Callable[[dict], bool] | None = None,
) -> dict[str, Any]:
    articles = law.get("articles", [])
    if flnos is not None:
        wanted = set(flnos)
        articles = [a for a in articles if a["flno"] in wanted]
    if article_filter:
        articles = [a for a in articles if article_filter(a)]

    all_rules: list[dict] = []
    for article in articles:
        all_rules.extend(extract_article(law, article, provider=provider))

    return {
        "law_code": law["law_code"],
        "law_name": law["law_name"],
        "version": law.get("amend_date"),
        "provider": provider,
        "article_count": len(articles),
        "rule_count": len(all_rules),
        "rules": all_rules,
    }
