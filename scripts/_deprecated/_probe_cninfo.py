"""Test cninfo for survey announcement category codes"""
import requests, json

# 巨潮资讯公告分类接口
CNINFO = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
H = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/", "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}

# 搜索调研公告 - 各种category组合
categories = [
    ("调研", "category_cgsd"),
    ("投资者", "category_tzgx"),
    ("路演", "category_luyan"),
    ("业绩说明", "category_yjsm"),
    ("", ""),  # 空=全部
]

for label, cat in categories:
    data = {
        "stock": "002180",
        "tabName": "fulltext",
        "pageSize": "5",
        "pageNum": "1",
        "searchkey": "调研活动" if label == "调研" else "",
        "secid": "",
        "category": cat,
    }
    try:
        r = requests.post(CNINFO, data=data, headers=H, timeout=10)
        j = r.json()
        items = j.get("announcements", []) if isinstance(j, dict) else []
        total = j.get("totalAnnouncement", 0) if isinstance(j, dict) else 0
        print(f"[{label or '全部'}] total={total}, returned={len(items)}")
        if items:
            for item in items[:2]:
                print(f"  - {item.get('announcementTime','')[:10]} | {item.get('announcementTypeName','')} | {item.get('announcementTitle','')[:60]}")
    except Exception as e:
        print(f"ERR [{label}]: {e}")

# 也测试东方财富的调研数据（直接从F10现有接口里找）
print("\n=== 东方财富F10现有接口（检查已知有效接口）===")
EM = "http://datacenter-web.eastmoney.com/api/data/v1/get"
EM_H = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.eastmoney.com/", "Accept": "application/json"}

# 从东方财富公告接口拉调研类型
survey_cats = [
    "category_tzzgx",
    "调研活动",
    "投资者关系活动",
]
for cat in survey_cats:
    params = {
        "reportName": "RPT_LICO_ANALYSIS",
        "columns": "ALL",
        "filter": '(SECUCODE="002180.SZ")',
        "pageNumber": "1", "pageSize": "5",
        "source": "WEB", "client": "WEB",
    }
    try:
        r = requests.get(EM, params=params, headers=EM_H, timeout=8)
        print(f"RPT_LICO_ANALYSIS: {r.text[:150]}")
    except Exception as e:
        print(f"ERR: {e}")
    break

# 测试东方财富公告 - 调研类型
print("\n=== 东方财富公告调研类别 ===")
EM_NEWS = "http://np-anotice-stock.eastmoney.com/api/security/ann"
params = {
    "sr": "-1", "page": "1", "pageSize": "10", "ann_type": "A", "stock_list": "600519"
}
try:
    r = requests.get(EM_NEWS, params={"sr": "-1", "page": "1", "pageSize": "10", "ann_type": "A", "stock_list": "600519"}, headers=EM_H, timeout=8)
    print(f"[{r.status_code}] {r.text[:400]}")
except Exception as e:
    print(f"ERR: {e}")
