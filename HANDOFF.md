# HANDOFF — 法規 ETL + Rule 抽取（黃蘭榛 / 富品盃）

更新：2026-08-04

## 這是什麼
台灣建築法規 ETL → Rule Spec v0 結構化抽取與人工覆核。全國法規資料庫 → normalized law JSON → 可覆核規則草稿。

## 目前狀態（可跑）
- ETL：`python etl.py --law D0070115 --refresh` → 389 條
- Rule 抽取：`python extract_rules.py --law-json data/output/D0070115.json --flnos 89,...,103`
  - 20 條輸入 → 37 條規則草稿；validation_errors=0
  - 產出 rules JSON + review CSV/JSON
- Gold：`data/gold/rule_extract_gold_v0.json`（20 條人工標註）
- 評測 field_accuracy 約 0.70–0.80（heuristic baseline）
- `pytest -q` → **17 passed**

## Notion 任務
- 「建立官方法規來源清單與版本欄位」→ 進行中
- 「實作法規 ETL 與條文切分」→ **完成**
- 「實作 LLM 條文結構化抽取與人工覆核格式」→ **完成**

## 檔案地圖
- `schemas/rule_spec_v0.json`｜`prompts/extract_rule_spec.md`
- `law_etl/rule_extract.py`（heuristic + 可選 openai）｜`rule_schema.py`｜`review.py`
- `extract_rules.py`｜`eval_extract.py`
- `data/gold/rule_extract_gold_v0.json`

## MVP active 規則包（給 Rule Engine）
- `data/mvp/mvp_rules_active_v0.json` — **11 條 active**（§90/91/92/93/95）
- `data/mvp/mvp_triage_v0.json` — 37 條 heuristic 篩選決策
- `docs/rule_engine_interface.md` — 給陳芊宇的接口說明

## 下一步
1. 陳芊宇確認 IR `target` 路徑與 scope DSL
2. （可選）`.env` 設 `OPENAI_API_KEY` 後跑 `--provider openai` 對齊 gold
3. Rule Engine 用 MVP 包做正負測試（見 interface doc §6）

## 開新對話接手 prompt
> 我是黃蘭榛，專案在 ~/Desktop/building-law-etl。請讀 HANDOFF.md。下一優先：人工覆核 review CSV、可選接 OpenAI provider 對齊 gold，並與 Rule Engine 對接 active 規則。
