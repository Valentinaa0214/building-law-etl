# HANDOFF — 法規 ETL（黃蘭榛 / 富品盃 AI Building Compliance Copilot）

更新：2026-07-19

## 這是什麼
台灣建築法規 ETL 與條文切分模組。全國法規資料庫（law.moj.gov.tw）→ 結構化 normalized law JSON，供下游 RAG / Rule Engine 使用。

## 目前狀態（可跑）
- ETL 骨架完成：`fetch → parse → segment → normalize → validate → load`
- `python etl.py --law D0070115` 離線跑通（fixture 5 條：§90/91/92/93/95）
- `pytest -q` 8 項全過（切分正確性 + 重跑一致性）
- content_hash 只依條文內容（不含 fetch_date）

## Notion 交付狀態（都在「研究生 → AI Building Compliance Copilot」workspace）
- 「建立官方法規來源清單與版本欄位」→ 進行中，來源表已寫入頁面
- 「實作法規 ETL 與條文切分」→ 進行中，設計 + 本骨架

## 下一步（讓兩張 P0 接近完成）
1. `parse.py` 接真實 law.moj.gov.tw HTML 版面解析（目前線上路徑只做通用去標籤）
2. `python etl.py --law D0070115 --refresh` 抓真實內容，條數衝到 ≥50（完整第四章 §85–103）
3. 跟陳芊宇對齊三類 MVP 規則適用的用途類組（來源表依賴其「三類 MVP 規則」）
4. 回填建築法（D0070109）最新修正日到 config.py / 來源表
5. 之後：LLM 條文結構化抽取（S1，7/25），輸出接 Rule Spec v0

## 檔案地圖
- `etl.py` CLI｜`law_etl/` 各 stage｜`data/fixtures/D0070115.txt` 離線樣本｜`tests/` 測試
- 尚未 git commit（等 蘭榛 決定）

## 開新對話用的接手 prompt
> 我是黃蘭榛，富品盃 AI Building Compliance Copilot 專案。專案在 ~/Desktop/building-law-etl（法規 ETL）。請讀 HANDOFF.md 接續：目標是把 parse.py 接真實 law.moj.gov.tw HTML、跑 --refresh 抓滿 §85–103（≥50 條），並保持 pytest 通過。
