#!/usr/bin/env python3
"""法規 ETL CLI。

用法：
    python etl.py --law D0070115
    python etl.py --law D0070115 --refresh   # 強制重新線上抓取
"""

from __future__ import annotations

import argparse
import logging
import sys

from law_etl.pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="全國法規資料庫 ETL 與條文切分")
    parser.add_argument("--law", required=True, help="法規代碼 PCode，例如 D0070115")
    parser.add_argument("--refresh", action="store_true", help="忽略快取，重新線上抓取")
    parser.add_argument("--base-dir", default=".", help="專案根目錄（預設當前目錄）")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    result = run(args.law, base_dir=args.base_dir, refresh=args.refresh)
    law = result["law"]
    print(
        f"{law['law_code']} {law['law_name']} | "
        f"條文數={len(law['articles'])} | "
        f"hash={law['content_hash'][:16]}… | "
        f"errors={len(result['errors'])} | "
        f"load={result['status']}"
    )
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
