"""Probe investor Q&A APIs"""
import requests, json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://irm.cninfo.com.cn/",
    "Accept": "application/json, text/plain, */*",
}

# Test 1: 互动易 - 东方财富irm平台
print("=== 互动易 IRM API ===")
# 东方财富投资者关系互动平台
urls_to_test = [
    # 互动易新API（东方财富irm）
    ("POST", "https://irm.cninfo.com.cn/ircsearch/", {"code": "002180", "pageNum": 1, "pageSize": 10}),
    # 旧版
    ("GET", "http://irm.cninfo.com.cn/ircsearch/?code=002180&page=1", None),
    # 东方财富股票问问
    ("GET", "https://guba.eastmoney.com/wenissearch?code=002180", None),
]

for method, url, data in urls_to_test:
    try:
        if method == "POST":
            r = requests.post(url, json=data, headers=HEADERS, timeout=10)
        else:
            r = requests.get(url, headers=HEADERS, timeout=10)
        print(f"[{r.status_code}] {url[:60]}")
        print(f"  Content-Type: {r.headers.get('Content-Type','')}")
        print(f"  Body preview: {r.text[:200]}")
        print()
    except Exception as e:
        print(f"[ERROR] {url[:60]}: {e}")
        print()

# Test 2: 上证e互动
print("=== 上证e互动 ===")
sse_urls = [
    "http://sns.sseinfo.com/company.php?type=0&code=600519",
    "https://sns.sseinfo.com/ajax/company.php?type=0&code=600519",
]
for url in sse_urls:
    try:
        h2 = dict(HEADERS, Referer="https://sns.sseinfo.com/")
        r = requests.get(url, headers=h2, timeout=10)
        print(f"[{r.status_code}] {url[:70]}")
        print(f"  Body: {r.text[:300]}")
        print()
    except Exception as e:
        print(f"[ERROR] {url}: {e}")

# Test 3: 巨潮资讯 - 业绩说明会
print("=== 巨潮业绩说明会 ===")
cninfo_urls = [
    ("POST", "http://www.cninfo.com.cn/new/hisAnnouncement/query", {
        "stock": "002180",
        "tabName": "fulltext",
        "pageSize": 10,
        "pageNum": 1,
        "searchkey": "业绩说明会",
        "secid": "",
        "category": "",
        "trade": "",
    }),
]
for method, url, data in cninfo_urls:
    try:
        h3 = dict(HEADERS, Referer="http://www.cninfo.com.cn/")
        r = requests.post(url, data=data, headers=h3, timeout=10)
        print(f"[{r.status_code}] {url[:70]}")
        print(f"  Body: {r.text[:400]}")
    except Exception as e:
        print(f"[ERROR] {e}")

print("\n=== Done ===")
