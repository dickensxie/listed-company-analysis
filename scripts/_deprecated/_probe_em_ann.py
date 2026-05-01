"""Parse EM announcement API - find survey/investor-relation types"""
import requests, json, urllib.parse

EM_ANN = "http://np-anotice-stock.eastmoney.com/api/security/ann"
H = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.eastmoney.com/", "Accept": "application/json"}

# Test with all announcement types for 600519
# Types: A=全部, B=公告, C=研报...
for stock, ann_type in [("600519", "A"), ("600519", "B"), ("600519", "C"), ("002180", "A")]:
    params = urllib.parse.urlencode({
        "sr": "-1", "page_index": "1", "page_size": "20",
        "ann_type": ann_type, "stock_list": stock,
        "board_type": "0"
    })
    url = f"{EM_ANN}?{params}"
    try:
        r = requests.get(url, headers=H, timeout=10)
        j = r.json()
        items = j.get("data", {}).get("list", []) if isinstance(j.get("data"), dict) else []
        total = j.get("data", {}).get("total", 0) if isinstance(j.get("data"), dict) else 0
        print(f"\n=== {stock} type={ann_type} total={total} returned={len(items)} ===")
        if items:
            # Show column names and categories
            cols_seen = {}
            for item in items:
                for col in item.get("columns", []):
                    cn = col.get("column_name", "")
                    cc = col.get("column_code", "")
                    cols_seen[cc] = cn
            print(f"Column types seen: {json.dumps(cols_seen, ensure_ascii=False)}")
            # Show first item full structure
            print(f"First item keys: {list(items[0].keys())}")
            print(f"First item: {json.dumps(items[0], ensure_ascii=False)[:600]}")
    except Exception as e:
        print(f"ERR {stock}/{ann_type}: {e}")
