# building-law-etl

台灣建築法規 ETL 與條文切分模組 —— **AI Building Compliance Copilot（富品盃）** 法規/NLP 工作流。

將全國法規資料庫（law.moj.gov.tw）的法規抓取、切分為結構化 `normalized law JSON`，
保留「編→章→節→條→項→款→目」層級與來源/版本，供下游 RAG 與 Rule Engine 使用。

## Pipeline

```
fetch → parse → segment → normalize → validate → load
```

| 階段 | 說明 |
| --- | --- |
| fetch | 取得原始內容（fixture / HTTP 快取 / 線上）|
| parse | HTML 去標籤或純文字轉條文文字 |
| segment | 依中文法條層級切分（章/節/條/項/款/目）|
| normalize | 套 schema、算 `content_hash`、補來源 URL 與版本欄位 |
| validate | 欄位/層級檢核，不合格標 `review_required` |
| load | 寫入 `data/output/{law_code}.json`（hash 未變則跳過）|

## 快速開始

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 用內建 fixture 離線跑（不需連網）
python etl.py --law D0070115

# 強制重新線上抓取
python etl.py --law D0070115 --refresh

# 測試（切分正確性 + 重跑一致性）
pytest -q
```

## 輸出 schema（摘要）

```json
{
  "law_code": "D0070115",
  "law_name": "建築技術規則建築設計施工編",
  "amend_date": "2026-02-23",
  "fetch_date": "2026-07-19",
  "content_hash": "sha256:…",
  "articles": [
    {
      "flno": "92",
      "chapter": "第四章 防火避難設施及消防設備",
      "section": "第一節 出入口、走廊、樓梯",
      "source_url": "https://law.moj.gov.tw/LawClass/LawSingle.aspx?flno=92&pcode=D0070115",
      "article_hash": "sha256:…",
      "review_status": "draft",
      "paragraphs": [
        {"no": 1, "text": "…", "subparagraphs": [{"label": "一", "text": "…", "items": []}]}
      ]
    }
  ]
}
```

## MVP 對應條文

| MVP 規則 | 條文 |
| --- | --- |
| 走道淨寬 | §92 |
| 出口/逃生距離（步行距離）| §93、§95 |
| 門/出口寬度 | §90、§91 |

## 版本流程

`draft → reviewed → active`，只有 `active` 條文才進 Rule Engine。
`content_hash` 只依條文內容（不含 `fetch_date`），供版本 diff 與重跑一致性檢查。

> 來源清單與版本欄位規範見 Notion：`建立官方法規來源清單與版本欄位`。

## 條文 → Rule Spec v0（LLM / heuristic 抽取）

第二階段：把 ETL 後的條文抽成可覆核的規則草稿。

| 交付物 | 路徑 |
| --- | --- |
| JSON Schema | `schemas/rule_spec_v0.json` |
| Prompt | `prompts/extract_rule_spec.md` |
| 抽取 CLI | `python extract_rules.py --law-json data/output/D0070115.json --flnos 89,...,103` |
| 人工覆核表 | `data/output/rules/*_review.csv`（gitignore）|
| Gold 評測集（20 條）| `data/gold/rule_extract_gold_v0.json` |
| 評測 | `python eval_extract.py --pred ... --gold ...` |

```bash
# 預設 heuristic（離線可重現）；有 OPENAI_API_KEY 可用 --provider openai
python extract_rules.py --law-json data/output/D0070115.json \
  --flnos 89,89-1,90,90-1,91,92,93,94,95,96,96-1,97,97-1,98,99,99-1,100,101,102,103

python eval_extract.py \
  --pred data/output/rules/D0070115_heuristic_rules.json \
  --gold data/gold/rule_extract_gold_v0.json
```

不確定欄位會寫入 `uncertain_fields`，並強制 `review_status=review_required`。
覆核流程：`draft/review_required → reviewed → active`（只有 active 進 Rule Engine）。

### MVP active 規則包（Rule Engine 載入）

| 檔案 | 說明 |
| --- | --- |
| `data/mvp/mvp_rules_active_v0.json` | 11 條 active 規則（§90/91/92/93/95）|
| `data/mvp/mvp_triage_v0.json` | 37→11 篩選決策 |
| `docs/rule_engine_interface.md` | Rule Engine 接口說明（給陳芊宇）|

### OpenAI（可選）

```bash
cp .env.example .env   # 填入 OPENAI_API_KEY，勿 commit
python extract_rules.py --law-json data/output/D0070115.json \
  --flnos 90,91,92,93,95 --provider openai
```

20 條評測約 **$0.01–0.05**（gpt-4o-mini）；預設 `heuristic` 不需 API。
