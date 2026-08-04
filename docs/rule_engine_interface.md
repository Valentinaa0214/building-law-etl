# Rule Engine 接口說明（給陳芊宇）

> 版本：v0｜更新：2026-08-04｜維護：黃蘭榛  
> 上游：`building-law-etl` 抽取 + 人工覆核  
> 下游：Hybrid Rule Engine 載入 `review_status=active` 規則

## 1. 資料流

```
ETL law JSON
  → extract_rules.py（heuristic / openai）
  → review CSV（approve / revise / reject）
  → mvp_rules_active_v0.json（僅 active）
  → Rule Engine.check(building_ir) → violations[]
```

**重要約束（技術手冊）：**

- 只有 `review_status === "active"` 的規則可進引擎
- LLM 只產草稿；判定邏輯必須 deterministic
- 每條 violation 必須能回溯 `source_quote` + `article` + `law_code`

## 2. 輸入：Building IR（引擎需讀取的欄位）

Rule Engine 對每條 active 規則，從 Building JSON IR 讀取 `target` 對應值：

| target | IR 路徑（建議） | 單位 | 說明 |
|--------|----------------|------|------|
| `exit.width_mm` | `floors[].exits[].width_mm` | mm | 出入口淨寬 |
| `exit.height_mm` | `floors[].exits[].height_mm` | mm | 出入口淨高 |
| `corridor.width_mm` | `floors[].corridors[].width_mm` | mm | 走廊淨寬 |
| `evac.walking_distance_m` | `floors[].rooms[].evac.walking_distance_m` 或 path graph 計算 | m | 居室任一點→樓梯口步行距離 |
| `stair.count` | `floors[].stairs.direct_stair_count` | count | 該層直通樓梯座數 |

**建議 IR 另帶 metadata（供 scope 過濾）：**

```json
{
  "building_use": ["B-2", "D-1"],
  "floor_index": 5,
  "is_evacuation_floor": false,
  "fire_resistant_structure": true,
  "corridors": [
    {
      "id": "C-501",
      "width_mm": 1500,
      "both_sides_habitable": true,
      "adjacent_room_floor_area_sqm": 250
    }
  ]
}
```

## 3. 規則物件格式（Rule Spec v0）

完整 JSON Schema：`schemas/rule_spec_v0.json`

引擎最小需讀欄位：

```json
{
  "rule_id": "MVP-EXIT-WIDTH-90",
  "law_code": "D0070115",
  "article": "90",
  "version": "2026-02-23",
  "review_status": "active",
  "scope": {
    "building_use": [],
    "conditions": ["location=evacuation_floor"]
  },
  "target": "exit.width_mm",
  "operator": ">=",
  "threshold": 1200,
  "unit": "mm",
  "source_quote": "…",
  "severity": "high"
}
```

### operator 語意

| operator | 判定 |
|----------|------|
| `>=` | `actual >= threshold` → pass |
| `<=` | `actual <= threshold` → pass |
| `>`, `<`, `==`, `!=` | 同上 |

### scope 過濾（建議實作順序）

1. **`scope.building_use`**：非空時，IR `building_use` 需有交集（或 IR 用途為所列類組之子集）
2. **`scope.conditions`**：字串 DSL，MVP 可先 hardcode 對照表：

| condition | 含義 |
|-----------|------|
| `location=evacuation_floor` | 只檢查避難層 |
| `location=non_evacuation_floor` | 只檢查非避難層 |
| `floor_index>=8` | 八層以上 |
| `corridor.both_sides_habitable` | 走廊兩側有居室 |
| `corridor.other` | 其他走廊（非兩側居室） |
| `exclude=A,B-1,...` | 排除用途 |

3. **`exceptions`**：MVP 可只記錄在 violation message，S2 再實作分支

## 4. 輸出：Violation 物件（建議格式）

```json
{
  "rule_id": "MVP-CORRIDOR-WIDTH-92-DEFAULT-OTHER",
  "status": "fail",
  "target": "corridor.width_mm",
  "actual": 980,
  "threshold": 1200,
  "operator": ">=",
  "unit": "mm",
  "severity": "high",
  "message": "走廊淨寬 980mm 小於規定 1200mm",
  "citation": {
    "law_code": "D0070115",
    "law_name": "建築技術規則建築設計施工編",
    "article": "92",
    "source_quote": "其 他 走 廊｜一‧二○公尺以上",
    "source_url": "https://law.moj.gov.tw/LawClass/LawSingle.aspx?flno=92&pcode=D0070115"
  },
  "evidence": {
    "floor_id": "F-5",
    "corridor_id": "C-501",
    "bbox": [120, 340, 880, 360]
  }
}
```

## 5. MVP 規則包

**檔案：** `data/mvp/mvp_rules_active_v0.json`  
**共 11 條 active 規則：**

| 類別 | rule_id | 法條 | target | 門檻 |
|------|---------|------|--------|------|
| 出入口寬 | MVP-EXIT-WIDTH-90 | §90 | exit.width_mm | ≥1200mm |
| 出入口高 | MVP-EXIT-HEIGHT-90 | §90 | exit.height_mm | ≥1800mm |
| 出入口寬 | MVP-EXIT-WIDTH-91 | §91 | exit.width_mm | ≥1200mm |
| 走道寬 | MVP-CORRIDOR-WIDTH-92-D34-BOTH | §92 | corridor.width_mm | ≥2400mm |
| 走道寬 | MVP-CORRIDOR-WIDTH-92-D34-OTHER | §92 | corridor.width_mm | ≥1800mm |
| 走道寬 | MVP-CORRIDOR-WIDTH-92-DEFAULT-BOTH | §92 | corridor.width_mm | ≥1600mm |
| 走道寬 | MVP-CORRIDOR-WIDTH-92-DEFAULT-OTHER | §92 | corridor.width_mm | ≥1200mm |
| 逃生距離 | MVP-EVAC-WALK-93-ABD1 | §93 | evac.walking_distance_m | ≤30m |
| 逃生距離 | MVP-EVAC-WALK-93-C | §93 | evac.walking_distance_m | ≤70m |
| 逃生距離 | MVP-EVAC-WALK-93-OTHER | §93 | evac.walking_distance_m | ≤50m |
| 樓梯數 | MVP-STAIR-COUNT-95-FLOOR8 | §95 | stair.count | ≥2 |

**載入範例（Python）：**

```python
import json

with open("data/mvp/mvp_rules_active_v0.json") as f:
    bundle = json.load(f)

active_rules = [r for r in bundle["rules"] if r["review_status"] == "active"]
assert len(active_rules) == 11
```

## 6. 正負測試案例（建議 Rule Engine 單元測試）

| case | 規則 | 輸入 | 預期 |
|------|------|------|------|
| T1-pass | MVP-EXIT-WIDTH-90 | exit.width_mm=1500, 避難層 | pass |
| T2-fail | MVP-EXIT-WIDTH-90 | exit.width_mm=1100, 避難層 | fail |
| T3-pass | MVP-CORRIDOR-WIDTH-92-DEFAULT-OTHER | corridor.width_mm=1200 | pass |
| T4-fail | MVP-CORRIDOR-WIDTH-92-DEFAULT-OTHER | corridor.width_mm=980 | fail |
| T5-pass | MVP-EVAC-WALK-93-ABD1 | use=B-2, distance=28m | pass |
| T6-fail | MVP-EVAC-WALK-93-ABD1 | use=B-2, distance=35m | fail |
| T7-pass | MVP-STAIR-COUNT-95-FLOOR8 | floor=10, stairs=2 | pass |
| T8-fail | MVP-STAIR-COUNT-95-FLOOR8 | floor=10, stairs=1 | fail |

## 7. 待對齊事項（請陳芊宇回覆）

1. **Building IR schema** — `target` 路徑是否與 VLM 輸出一致？需共同定義 enum
2. **scope DSL** — MVP 用字串 conditions 還是改 JSON 結構？
3. **多規則衝突** — 同一 corridor 命中 D-3 與 default，取最嚴？
4. **§92 F-1 組** — S2 補 1600/1200 兩條；MVP 可先略
5. **例外條款** — `exceptions[]` 先 warning 還是 skip？

## 8. 相關檔案

| 檔案 | 用途 |
|------|------|
| `schemas/rule_spec_v0.json` | 完整 schema |
| `data/mvp/mvp_rules_active_v0.json` | **引擎載入此檔** |
| `data/mvp/mvp_triage_v0.json` | 37→11 篩選決策 |
| `data/output/rules/*_review.csv` | 人工覆核表 |
| `prompts/extract_rule_spec.md` | LLM 抽取 prompt |

聯絡：黃蘭榛（NLP/RAG/法規 Agent）
