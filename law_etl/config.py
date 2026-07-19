"""官方法規來源登錄（對應 Notion『建立官方法規來源清單與版本欄位』）。

只採全國法規資料庫（law.moj.gov.tw）為唯一一手來源。
"""

from __future__ import annotations

LAW_SINGLE_URL = "https://law.moj.gov.tw/LawClass/LawSingle.aspx?flno={flno}&pcode={pcode}"

LAW_SOURCES: dict[str, dict] = {
    "D0070115": {
        "law_code": "D0070115",
        "law_name": "建築技術規則建築設計施工編",
        "competent_authority": "內政部國土管理署",
        "official_url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=D0070115",
        "history_url": "https://law.moj.gov.tw/LawClass/LawHistory.aspx?pcode=D0070115",
        "part": "建築設計施工編",
        "publish_date": "1945-02-26",
        "amend_date": "2026-02-23",
        "effective_status": "in_force",
    },
    "D0070141": {
        "law_code": "D0070141",
        "law_name": "建築物使用類組及變更使用辦法",
        "competent_authority": "內政部國土管理署",
        "official_url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=D0070141",
        "history_url": "https://law.moj.gov.tw/LawClass/LawHistory.aspx?pcode=D0070141",
        "part": "",
        "publish_date": "2004-09-14",
        "amend_date": "2025-05-13",
        "effective_status": "in_force",
    },
    # 建築法（母法）：最新修正日待抓取確認後回填。
    "D0070109": {
        "law_code": "D0070109",
        "law_name": "建築法",
        "competent_authority": "內政部",
        "official_url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=D0070109",
        "history_url": "https://law.moj.gov.tw/LawClass/LawHistory.aspx?pcode=D0070109",
        "part": "",
        "publish_date": None,
        "amend_date": None,
        "effective_status": "unknown",
    },
}


def get_source(law_code: str) -> dict:
    if law_code not in LAW_SOURCES:
        raise KeyError(f"未登錄的法規代碼: {law_code}（請先加入 config.LAW_SOURCES）")
    return LAW_SOURCES[law_code]
