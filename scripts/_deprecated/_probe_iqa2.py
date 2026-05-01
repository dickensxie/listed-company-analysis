"""Deep probe investor Q&A APIs"""
import requests, json, re

HEADERS_BASIC = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json, */*"}
HEADERS_EZ = {"User-Agent": "Mozilla/5.0", "Referer": "https://irm.eastmoney.com", "Accept": "application/json"}
HEADERS_CNINFO = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn", "Accept": "application/json"}
HEADERS_SSE = {"User-Agent": "Mozilla/5.0", "Referer": "https://sns.sseinfo.com", "Accept": "application/json"}

results = {}

# 1. 东方财富 问问/股吧问答 API
print("=== 东方财富问问 ===")
ez_urls = [
    ("GET", "https://guba.eastmoney.com/search?keyword=纳思达+投资者&type=qa", None),
    ("GET", "https://guba.eastmoney.com/question?q=纳思达&type=answer", None),
    # 东方财富irm平台API
    ("GET", "https://irm.eastmoney.com/ircsearch?code=002180&type=2&pageindex=0", None),
    ("GET", "https://irm.eastmoney.com/ir_Q_A?q=002180&pi=0&ps=20", None),
    # 新API
    ("GET", "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_QA_LIST&columns=ALL&filter=(SECUCODE=%22002180.SZ%22)&pageNumber=1&pageSize=20&source=WEB&client=WEB", None),
]
for method, url, data in ez_urls:
    try:
        r = requests.get(url, headers=HEADERS_EZ, timeout=8)
        print(f"[{r.status_code}] {url[30:80]}")
        print(f"  {r.text[:150]}")
        print()
    except Exception as e:
        print(f"[ERR] {url[30:60]}: {e}")

# 2. 巨潮资讯 互动问答
print("=== 巨潮资讯互动易 ===")
cninfo_tries = [
    ("POST", "http://www.cninfo.com.cn/new/information/topSearch/query", {
        "keyWord": "纳思达", "maxSecNum": 5, "maxAnnNum": 5
    }),
    ("POST", "http://www.cninfo.com.cn/new/investor/q&a/query", {
        "stock": "002180", "pageNum": 1, "pageSize": 20
    }),
    ("POST", "http://www.cninfo.com.cn/new/question/list", {
        "code": "002180", "page": 1, "limit": 10
    }),
    # 标准东方财富F10接口测试
    ("GET", "http://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_QA_LIST&filter=(SECUCODE=%22002180.SZ%22)&pageNumber=1&pageSize=20&source=WEB&client=WEB", None),
    ("GET", "http://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_INTERACT_QA&filter=(SECUCODE=%22002180.SZ%22)&pageNumber=1&pageSize=20&source=WEB&client=WEB", None),
    ("GET", "http://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_IR_QA&filter=(SECUCODE=%22002180.SZ%22)&pageNumber=1&pageSize=20&source=WEB&client=WEB", None),
]
for method, url, data in cninfo_tries:
    try:
        if method == "POST":
            r = requests.post(url, data=data, headers=HEADERS_CNINFO, timeout=8)
        else:
            r = requests.get(url, headers=HEADERS_BASIC, timeout=8)
        print(f"[{r.status_code}] {url[35:90]}")
        print(f"  {r.text[:200]}")
        print()
    except Exception as e:
        print(f"[ERR] {url[35:65]}: {e}")

# 3. 上交所/深交所互动平台
print("=== 交易所互动平台 ===")
exchange_tries = [
    ("GET", "https://sns.sseinfo.com/ajax/company.php?type=0&code=600519&page=1", None),
    ("GET", "https://sns.sseinfo.com/interaction/getInteractionListByCode.do?code=600519&pageNum=1&pageSize=20", None),
    ("GET", "https://irm.sse.com.cn/irm/eastmoney?code=600519&type=qa&page=1", None),
    ("GET", "https://irm.szse.cn/api/content/search?code=002180&type=qa&pageIndex=1&pageSize=20", None),
]
for method, url, data in exchange_tries:
    try:
        r = requests.get(url, headers=HEADERS_SSE, timeout=8)
        print(f"[{r.status_code}] {url[25:75]}")
        print(f"  {r.text[:200]}")
        print()
    except Exception as e:
        print(f"[ERR] {url[25:60]}: {e}")

# 4. 尝试东方财富F10平台已知有效的报表名称前缀猜测
print("=== 东方财富F10 报表名猜测 ===")
f10_tries = [
    "RPT_F10_QA", "RPT_F10_QALIST", "RPT_F10_INVESTOR_QA",
    "RPT_F10_INTERACT", "RPT_F10_HDQQ", "RPT_F10_INTERACTION",
    "RPT_F10_IRM_QA", "RPT_F10_QUESTION",
]
for rname in f10_tries:
    url = f"http://datacenter-web.eastmoney.com/api/data/v1/get?reportName={rname}&filter=(SECUCODE=%22002180.SZ%22)&pageNumber=1&pageSize=5&source=WEB&client=WEB"
    try:
        r = requests.get(url, headers=HEADERS_BASIC, timeout=6)
        text = r.text[:100]
        status = "✅" if '"data":' in r.text or '"result":' in r.text else "❌"
        print(f"{status} [{r.status_code}] {rname}: {text[:80]}")
    except Exception as e:
        print(f"❌ {rname}: {e}")

print("\n=== Done ===")
