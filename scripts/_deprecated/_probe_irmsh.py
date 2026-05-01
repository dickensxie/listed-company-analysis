"""Test irsh.eastmoney.com APIs with proper encoding"""
import requests, json

EM_IRSH = "https://irsh.eastmoney.com/ajax"
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://irsh.eastmoney.com/",
    "Accept": "application/json",
}

def get_json(r):
    if r.status_code != 200:
        return {"_error": f"HTTP {r.status_code}"}
    ct = r.headers.get("Content-Type", "")
    # Try utf-8 first, then gbk
    for enc in ["utf-8", "gbk", "gb2312"]:
        try:
            r.encoding = enc
            text = r.text
            j = json.loads(text)
            return j
        except Exception:
            pass
    return {"_error": "all encodings failed", "_raw": r.text[:200]}

targets = [
    ("调研记录", f"{EM_IRSH}/CompanySurveyList?code=600519&pageindex=1&pagesize=20"),
    ("Q&A", f"{EM_IRSH}/CompanyQA?code=600519&pageindex=1&pagesize=20"),
    ("路演", f"{EM_IRSH}/CompanyRoadshow?code=600519&pageindex=1&pagesize=20"),
    ("业绩说明", f"{EM_IRSH}/CompanyPerformance?code=600519&pageindex=1&pagesize=20"),
]

for label, url in targets:
    try:
        r = requests.get(url, headers=H, timeout=10)
        j = get_json(r)
        if "_error" in j:
            print(f"FAIL [{label}]: {j}")
        else:
            print(f"OK [{label}]: {json.dumps(j, ensure_ascii=False)[:400]}")
    except Exception as e:
        print(f"ERR [{label}]: {e}")

# Also test EM datacenter survey
print("\n=== EM datacenter survey ===")
EM = "http://datacenter-web.eastmoney.com/api/data/v1/get"
EM_H = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.eastmoney.com/", "Accept": "application/json"}
survey_names = [
    "RPT_F10_RESEARCH_VISIT_RECORD",
    "RPT_F10_ORG_SURVEY_LIST",
    "RPT_F10_SURVEY_LIST_V2",
    "RPT_F10_SURVEY_RECORD",
]
for rname in survey_names:
    params = {
        "reportName": rname,
        "columns": "ALL",
        "filter": '(SECUCODE="600519.SH")',
        "pageNumber": "1", "pageSize": "5",
        "source": "WEB", "client": "WEB",
    }
    try:
        r = requests.get(EM, params=params, headers=EM_H, timeout=10)
        j = r.json()
        raw = j.get("result", {}).get("data", [])
        count = len(raw) if isinstance(raw, list) else 0
        if count > 0:
            print(f"OK {rname}: {count} records")
            print(f"   Keys: {list(raw[0].keys())}")
            print(f"   {json.dumps(raw[0], ensure_ascii=False)[:300]}")
        else:
            print(f"empty {rname}")
    except Exception as e:
        print(f"ERR {rname}: {e}")
