"""Final probe - fix GBK encoding + find real survey/QA APIs"""
import requests, json

EM_IRSH = "https://irsh.eastmoney.com/ajax"
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://irsh.eastmoney.com/", "Accept": "application/json"}

def fetch_json(url, headers=None, timeout=10):
    """Properly handle GBK responses"""
    h = headers or H
    r = requests.get(url, headers=h, timeout=timeout)
    if r.status_code != 200:
        return {"_error": f"HTTP {r.status_code}"}
    # Try UTF-8 first
    try:
        return r.json()
    except Exception:
        pass
    # Try GBK with errors='replace'
    try:
        text = r.content.decode("gbk", errors="replace")
        return json.loads(text)
    except Exception:
        pass
    return {"_error": "decode failed", "_raw": r.content[:200]}

targets = [
    ("调研", f"{EM_IRSH}/CompanySurveyList?code=600519&pageindex=1&pagesize=20"),
    ("QA", f"{EM_IRSH}/CompanyQA?code=600519&pageindex=1&pagesize=20"),
    ("路演", f"{EM_IRSH}/CompanyRoadshow?code=600519&pageindex=1&pagesize=20"),
    ("业绩", f"{EM_IRSH}/CompanyPerformance?code=600519&pageindex=1&pagesize=20"),
]

for label, url in targets:
    j = fetch_json(url)
    if "_error" in j:
        print(f"ERR [{label}]: {j}")
    else:
        print(f"OK [{label}]: {json.dumps(j, ensure_ascii=False)[:400]}")

# EM datacenter - test with raw response
print("\n=== EM datacenter ===")
EM = "http://datacenter-web.eastmoney.com/api/data/v1/get"
EM_H = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.eastmoney.com/", "Accept": "application/json"}
for rname in ["RPT_F10_RESEARCH_VISIT_RECORD", "RPT_F10_ORG_SURVEY_LIST"]:
    params = {"reportName": rname, "columns": "ALL", "filter": '(SECUCODE="600519.SH")',
              "pageNumber": "1", "pageSize": "5", "source": "WEB", "client": "WEB"}
    try:
        r = requests.get(EM, params=params, headers=EM_H, timeout=10)
        print(f"[{r.status_code}] {rname}: {r.text[:200]}")
    except Exception as e:
        print(f"ERR {rname}: {e}")
