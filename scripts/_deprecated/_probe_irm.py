"""Probe eastmoney IRM web APIs directly"""
import requests, json

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://irm.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://irm.eastmoney.com",
}

# 东方财富 IRM 平台 AJAX 接口
urls = [
    # 调研记录
    ("调研记录", "GET", "https://irm.eastmoney.com/iraction/2?code=600519&pi=1&ps=20"),
    ("调研记录v2", "GET", "https://irm.eastmoney.com/ir_Q_A?code=600519&type=survey&pi=0&ps=20"),
    ("调研记录v3", "GET", "https://irm.eastmoney.com/iraction/survey?code=600519&page=1&size=20"),
    # Q&A
    ("Q&A", "GET", "https://irm.eastmoney.com/ir_Q_A?code=600519&type=qa&pi=0&ps=20"),
    ("Q&A v2", "GET", "https://irm.eastmoney.com/irquestion?code=600519&page=1"),
    # 路演
    ("路演", "GET", "https://irm.eastmoney.com/iraction/1?code=600519&pi=1&ps=20"),
    ("路演v2", "GET", "https://irm.eastmoney.com/iraction/roadshow?code=600519&page=1&size=20"),
    # 业绩说明会
    ("业绩说明", "GET", "https://irm.eastmoney.com/iraction/presentation?code=600519&page=1&size=20"),
    # 数据中心EM调研接口
    ("EM调研", "GET", "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_RESEARCH_VISIT_RECORD&filter=(SECUCODE=%22600519.SH%22)&pageNumber=1&pageSize=10&source=WEB&client=WEB"),
    ("EM调研2", "GET", "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_ORG_SURVEY_LIST&filter=(SECUCODE=%22600519.SH%22)&pageNumber=1&pageSize=10&source=WEB&client=WEB"),
    # 巨潮资讯IRM
    ("巨潮IRM", "POST", "https://irm.cninfo.com.cn/ircsearch/", {"code": "600519", "pageNum": 1, "pageSize": 10, "type": "all"}),
]

for label, method, url, *extra in urls:
    data = extra[0] if extra else None
    try:
        if method == "POST":
            r = requests.post(url, json=data if data and isinstance(data, dict) else None,
                            data=data if data and isinstance(data, str) else None,
                            headers=H, timeout=10)
        else:
            r = requests.get(url, headers=H, timeout=10)
        print(f"[{r.status_code}] {label}: {url[30:75]}")
        print(f"  Content-Type: {r.headers.get('Content-Type','')[:60]}")
        preview = r.text[:250].replace('\n',' ')
        print(f"  Preview: {preview}")
        print()
    except Exception as e:
        print(f"[ERR] {label}: {e}")
        print()
