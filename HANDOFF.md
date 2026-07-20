# HANDOFF — 法規 ETL（黃蘭榛 / 富品盃 AI Building Compliance Copilot）

更新：2026-07-19（parse 接真實 HTML + --refresh 全文）

## 這是什麼
台灣建築法規 ETL 與條文切分模組。全國法規資料庫（law.moj.gov.tw）→ 結構化 normalized law JSON，供下游 RAG / Rule Engine 使用。

## 目前狀態（可跑）
- ETL：`fetch → parse → segment → normalize → validate → load`
- `parse.py` 已專用解析 law.moj.gov.tw LawAll（`#pnLawFla .law-reg-content`）
- `python etl.py --law D0070115 --refresh` → **389 條**，errors=0（含完整第四章；§85–103 共 25 條，該區間官方就這麼多）
- `pytest -q` **11 passed**（切分 / 重跑一致 / MOJ HTML 解析）
- fetch：cache > fixture > online；SSL 對官方站 `verify=False`（環境憑證鏈問題）

## Notion 交付狀態
- 「建立官方法規來源清單與版本欄位」→ 進行中
- 「實作法規 ETL 與條文切分」→ 接近完成（≥50 條已達；§90–95 切分正確）

## 下一步
1. 跟陳芊宇對齊三類 MVP 規則適用的用途類組
2. 回填建築法（D0070109）最新修正日到 config.py / 來源表
3. 人工核對 §90/91/92/93/95 原文；表格欄位可後續結構化進 `tables`
4. 之後：LLM 條文結構化抽取（S1），輸出接 Rule Spec v0

## 檔案地圖
- `etl.py` CLI｜`law_etl/` 各 stage
- `data/fixtures/D0070115.txt` 離線 MVP 樣本｜`D0070115_moj_sample.html` 解析測試
- `data/raw/`、`data/output/` 執行產物（gitignore）
- 已 commit：真實 HTML 解析與 fetch 穩定化

## 開新對話用的接手 prompt
> 我是黃蘭榛，富品盃 AI Building Compliance Copilot 專案。專案在 ~/Desktop/building-law-etl（法規 ETL）。請讀 HANDOFF.md 接續：下一優先是對齊用途類組、回填建築法修正日，並準備 LLM 條文→Rule Spec 抽取。
