"""Fix cninfo probe and test survey announcements"""
import requests, json

CNINFO = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
H = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/", "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}

# Test 1: cninfo announcement search with secid
print("=== CNINFO announcement search ===")
# Get secid first using a known working stock
for code, plate in [("600519", "sh"), ("002180", "sz")]:
    data = {
        "stock": code,
        "tabName": "fulltext",
        "pageSize": "5",
        "pageNum": "1",
        "searchkey": "",
        "secid": f"{plate}.{code}",
        "category": "",
    }
    try:
        r = requests.post(CNINFO, data=data, headers=H, timeout=10)
        j = r.json()
        anns = j.get("announcements") if isinstance(j, dict) else None
        total = j.get("totalAnnouncement", 0) if isinstance(j, dict) else 0
        print(f"  [{code}] total={total}, returned={len(anns) if anns else 0}")
        if anns and len(anns) > 0:
            for a in anns[:3]:
                print(f"    {a.get('announcementTime','')[:10]} | {a.get('announcementTypeName','')[:30]} | {a.get('announcementTitle','')[:60]}")
    except Exception as e:
        print(f"  ERR [{code}]: {e} | body: {r.text[:200] if 'r' in dir() else 'N/A'}")

# Test 2: EM announcement API with correct params
print("\n=== EM announcement API ===")
EM_ANN = "http://np-anotice-stock.eastmoney.com/api/security/ann"
EM_H = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.eastmoney.com/", "Accept": "application/json"}
ann_urls = [
    "http://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_index=1&page_size=10&ann_type=A&stock_list=600519",
    "http://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_index=1&page_size=10&ann_type=A&stock_list=600519&board_type=0",
]
for url in ann_urls:
    try:
        r = requests.get(url, headers=EM_H, timeout=10)
        print(f"[{r.status_code}] {url[45:90]}")
        print(f"  {r.text[:400]}")
    except Exception as e:
        print(f"ERR: {e}")

# Test 3: cninfo survey-specific categories
print("\n=== CNINFO survey categories ===")
for code, plate in [("002180", "sz")]:
    for searchkey in ["调研活动", "机构调研", "投资者关系活动"]:
        data = {
            "stock": code,
            "tabName": "fulltext",
            "pageSize": "10",
            "pageNum": "1",
            "searchkey": searchkey,
            "secid": f"{plate}.{code}",
            "category": "",
        }
        try:
            r = requests.post(CNINFO, data=data, headers=H, timeout=10)
            j = r.json()
            anns = j.get("announcements") if isinstance(j, dict) else None
            total = j.get("totalAnnouncement", 0) if isinstance(j, dict) else 0
            if anns and len(anns) > 0:
                print(f"  [{searchkey}] total={total}, returned={len(anns)}")
                for a in anns[:3]:
                    print(f"    {a.get('announcementTime','')[:10]} | {a.get('announcementTitle','')[:70]}")
        except Exception as e:
            print(f"  ERR [{searchkey}]: {e}")
