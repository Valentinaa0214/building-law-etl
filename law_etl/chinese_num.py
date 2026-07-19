"""中文數字與全形字元處理工具。"""

from __future__ import annotations

_CN_DIGIT = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}


def cn_to_int(text: str) -> int | None:
    """將『四』『十五』『二十』等中文數字轉為整數（支援到百位）。"""
    s = (text or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)

    total = 0
    current = 0
    for ch in s:
        if ch in _CN_DIGIT:
            current = _CN_DIGIT[ch]
        elif ch == "十":
            total += (current or 1) * 10
            current = 0
        elif ch == "百":
            total += (current or 1) * 100
            current = 0
        else:
            return None
    return total + current


def normalize_digits(text: str) -> str:
    """全形數字→半形、全形空白→半形空白；保留中文標點（（）、）。"""
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:            # 全形空白
            out.append(" ")
        elif 0xFF10 <= code <= 0xFF19:  # 全形 0-9
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)
