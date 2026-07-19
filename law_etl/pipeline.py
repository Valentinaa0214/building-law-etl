"""pipeline 編排：fetch -> parse -> segment -> normalize -> validate -> load。

- idempotent：輸出已存在且 content_hash 相同 → 跳過寫入（重跑一致）。
- logging：每 stage 記錄；失敗項寫 logs/errors-{run_id}.jsonl，不中斷整批。
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid

from . import config, fetch, normalize as normalize_mod, parse, segment as segment_mod, validate as validate_mod

logger = logging.getLogger("law_etl")


def run(law_code: str, base_dir: str = ".", refresh: bool = False) -> dict:
    """執行單一法規 ETL，回傳 {law, errors, status, run_id}。"""
    run_id = uuid.uuid4().hex[:8]
    cfg = config.get_source(law_code)
    logger.info("[%s] start law=%s refresh=%s", run_id, law_code, refresh)

    t0 = time.perf_counter()
    raw, fetch_date = fetch.fetch_raw(cfg, base_dir=base_dir, refresh=refresh)
    text = parse.parse_raw(raw)
    articles = segment_mod.segment(text, part=cfg.get("part", ""))
    meta = {**cfg, "fetch_date": fetch_date}
    law = normalize_mod.normalize(meta, articles)
    errors = validate_mod.validate(law)
    logger.info(
        "[%s] segmented=%d errors=%d hash=%s (%.3fs)",
        run_id, len(law["articles"]), len(errors), law["content_hash"][:16],
        time.perf_counter() - t0,
    )

    if errors:
        _write_errors(base_dir, run_id, law_code, errors)

    status = _load(base_dir, law)
    return {"law": law, "errors": errors, "status": status, "run_id": run_id}


def _load(base_dir: str, law: dict) -> str:
    """idempotent 寫入：hash 未變則跳過。"""
    out_dir = os.path.join(base_dir, "data", "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{law['law_code']}.json")

    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
        if old.get("content_hash") == law["content_hash"]:
            logger.info("content_hash unchanged -> skip write (%s)", path)
            return "skipped"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(law, f, ensure_ascii=False, indent=2, sort_keys=True)
    return "written"


def _write_errors(base_dir: str, run_id: str, law_code: str, errors: list[dict]) -> None:
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"errors-{run_id}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for e in errors:
            f.write(json.dumps({"law_code": law_code, **e}, ensure_ascii=False) + "\n")
    logger.warning("wrote %d error(s) -> %s", len(errors), path)
