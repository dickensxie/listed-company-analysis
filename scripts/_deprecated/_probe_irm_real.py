"""Test the exact irsh.eastmoney.com URLs that returned data"""
import requests, json

# From probe1, these returned valid data:
# RPT_F10_RESEARCH_VISIT_RECORD (5 records)
# RPT_F10_ORG_SURVEY_LIST (5 records)
# RPT_F10_INTERACT (5 records) - from first probe

H = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.eastmoney.com/", "Accept": "application/json"}
EM = "http://datacenter-web.eastmoney.com/api/data/v1/get"

targets = [
    ("600519.SH", "RPT_F10_RESEARCH_VISIT_RECORD"),
    ("600519.SH", "RPT_F10_ORG_SURVEY_LIST"),
    ("600519.SH", "RPT_F10_INTERACT"),
    ("002180.SZ", "RPT_F10_RESEARCH_VISIT_RECORD"),
    ("002180.SZ", "RPT_F10_ORG_SURVEY_LIST"),
]

for code, rname in targets:
    params = {
        "reportName": rname,
        "columns": "ALL",
        "filter": f'(SECUCODE="{code}")',
        "pageNumber": "1", "pageSize": "5",
        "source": "WEB", "client": "WEB",
    }
    try:
        r = requests.get(EM, params=params, headers=H, timeout=10)
        j = r.json()
        raw = j.get("result", {}).get("data", [])
        count = len(raw) if isinstance(raw, list) else 0
        print(f"[{count:2d}] {rname} ({code}): {json.dumps(raw[0], ensure_ascii=False)[:200] if raw else 'empty'}")
    except Exception as e:
        print(f"[ER] {rname} ({code}): {e}")

# Also test EM irsh.eastmoney.com AJAX API
print("\n=== EM irsh AJAX ===")
irsh_urls = [
    "https://irsh.eastmoney.com/ajax/CompanySurveyList?code=600519&pageindex=1&pagesize=20",
    "https://irsh.eastmoney.com/ajax/CompanyInfo?code=600519",
    "https://irsh.eastmoney.com/ajax/CompanyQA?code=600519&pageindex=1&pagesize=20",
    "https://irsh.eastmoney.com/ajax/CompanyRoadshow?code=600519&pageindex=1&pagesize=20",
]
for url in irsh_urls:
    h2 = {"User-Agent": "Mozilla/5.0", "Referer": "https://irsh.eastmoney.com/", "Accept": "application/json"}
    try:
        r = requests.get(url, headers=h2, timeout=10)
        print(f"[{r.status_code}] {url[25:70]}")
        print(f"  {r.text[:200]}")
    except Exception as e:
        print(f"[ER] {url[25:55]}: {e}")
