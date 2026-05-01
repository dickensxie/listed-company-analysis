"""Search EM datacenter for valid survey/roadshow/IR report names"""
import requests, json

EM_API = "http://datacenter-web.eastmoney.com/api/data/v1/get"
H = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.eastmoney.com/", "Accept": "application/json", "Accept-Language": "zh-CN"}

# 从EM公开文档/F10页面试过的真实报表名前缀猜测
prefixes = [
    "RPT_F10_IR_", "RPT_F10_SURVEY", "RPT_F10_ORG_", "RPT_F10_VISIT",
    "RPT_F10_RESEARCH_", "RPT_F10_INTERACT", "RPT_F10_ROADSHOW",
    "RPT_F10_MEETING", "RPT_F10_PRESENTATION", "RPT_F10_QA",
    "RPT_F10_QUESTION", "RPT_F10_IROADSHOW", "RPT_F10_IPRESENTATION",
    "RPT_F10_ISURVEY", "RPT_F10_IQ_A", "RPT_F10_IQALIST",
]

secucode = "600519.SH"
successes = []

for prefix in prefixes:
    for suffix in ["LIST", "LIST_V2", "_LIST", "RECORD", "_RECORD", "INFO", ""]:
        rname = prefix + suffix
        if rname.count('_') < 2:
            continue
        params = {
            "reportName": rname,
            "columns": "ALL",
            "filter": f'(SECUCODE="{secucode}")',
            "pageNumber": "1", "pageSize": "3",
            "source": "WEB", "client": "WEB",
        }
        try:
            r = requests.get(EM_API, params=params, headers=H, timeout=5)
            j = r.json()
            if j.get("success") and j.get("result"):
                raw = j.get("result", {}).get("data") or []
                count = len(raw) if isinstance(raw, list) else 0
                if count > 0:
                    print(f"✅ [{count:2d}] {rname}")
                    successes.append((rname, raw[0] if raw else {}))
            else:
                # still might have partial data
                if j.get("message") == "success" or j.get("code") == 0:
                    print(f"~ [{rname[:40]}] partial")
        except Exception:
            pass

print(f"\nTotal successes: {len(successes)}")
for rname, sample in successes[:10]:
    print(f"\n=== {rname} ===")
    print(f"Keys: {list(sample.keys())}")
    print(f"Data: {json.dumps(sample, ensure_ascii=False)[:400]}")
