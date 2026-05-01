"""Test which EM F10 report names return data for 600519"""
import requests, json

EM_API = "http://datacenter-web.eastmoney.com/api/data/v1/get"
H = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.eastmoney.com/", "Accept": "application/json"}
secucode = "600519.SH"

# 之前探测发现返回有效的报表名
candidates = [
    "RPT_F10_INTERACT",
    "RPT_F10_HDQQ",
    "RPT_F10_INTERACTION",
    "RPT_F10_IRM_QA",
    "RPT_F10_IRM_LIST",
    "RPT_F10_INTERACT_LIST",
    "RPT_F10_SURVEY_LIST",
    "RPT_F10_ORG_SURVEY",
    "RPT_F10_RESEARCH_VISIT",
    "RPT_F10_SURVEY_RECORD",
    "RPT_F10_VISIT_LIST",
    "RPT_F10_ORG_VISIT",
    "RPT_F10_IR_ACTIVITY",
    "RPT_F10_IR_ACTIVITIES",
    "RPT_F10_ROADSHOW_LIST",
    "RPT_F10_PERFORMANCE_PRESENTATION",
    "RPT_F10_PERFORMANCE_LIST",
    "RPT_F10_IR_ROADSHOW",
    "RPT_F10_IR_QALIST",
    "RPT_F10_IR_Q_A",
    "RPT_F10_IRQUESTION",
    "RPT_F10_QUESTION",
    "RPT_F10_INVESTORQUESTION",
]

results = []
for rname in candidates:
    params = {
        "reportName": rname,
        "columns": "ALL",
        "filter": f'(SECUCODE="{secucode}")',
        "pageNumber": "1", "pageSize": "5",
        "source": "WEB", "client": "WEB",
    }
    try:
        r = requests.get(EM_API, params=params, headers=H, timeout=8)
        j = r.json()
        count = 0
        # Try to count items
        raw = j
        for key in ["result", "data"]:
            if isinstance(raw, dict):
                raw = raw.get(key)
        if isinstance(raw, list):
            count = len(raw)
        elif isinstance(raw, dict) and "data" in raw:
            count = len(raw.get("data", []))
        
        results.append((rname, count, j))
        print(f"[{count:2d}] {rname}")
    except Exception as e:
        print(f"[ ER] {rname}: {e}")

print()
# Show fields from the first non-empty result
for rname, count, j in results:
    if count > 0:
        print(f"\n=== {rname} (count={count}) ===")
        raw = j
        for key in ["result", "data"]:
            if isinstance(raw, dict):
                raw = raw.get(key)
        if isinstance(raw, list) and raw:
            item = raw[0]
            print(f"Keys: {list(item.keys())}")
            print(f"Sample: {json.dumps(item, ensure_ascii=False)[:300]}")
        break
