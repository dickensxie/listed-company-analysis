"""探索北交所公告API"""
import requests
import json
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 尝试北交所各种可能的API端点
test_urls = [
    # 公告列表
    'https://www.bse.cn/nqxxController/nqxx.do?callback=jsonpCallback',
    'https://www.bse.cn/newdisclosure/newdisclosure.do',
    'https://www.bse.cn/api/newdisclosure/newdisclosure.do',
    
    # 上市公司列表（可能包含公告）
    'https://www.bse.cn/api/list/listCompany',
    'https://www.bse.cn/nqxxController/queryCompanyList.do',
    
    # 信息披露
    'https://www.bse.cn/disclosureInfoController/disclosureInfo.do',
]

print('=== 探索北交所API端点 ===\n')

for url in test_urls:
    try:
        # GET请求
        r = requests.get(url, headers=headers, timeout=5)
        print(f'GET {url}')
        print(f'  状态: {r.status_code}, 长度: {len(r.text)}')
        
        if r.status_code == 200 and len(r.text) > 100:
            # 尝试JSON解析
            try:
                data = r.json()
                print(f'  JSON键: {list(data.keys())[:5]}')
            except:
                # 可能是JSONP
                if 'callback' in url.lower():
                    match = re.search(r'callback\((.*)\)', r.text)
                    if match:
                        data = json.loads(match.group(1))
                        print(f'  JSONP解析成功，键: {list(data.keys())[:5]}')
        print()
    except Exception as e:
        print(f'  错误: {e}\n')

# 尝试POST请求
print('=== 测试POST请求 ===\n')
post_urls = [
    ('https://www.bse.cn/nqxxController/nqxx.do', {'type': 'disclosure'}),
    ('https://www.bse.cn/disclosureInfoController/disclosureInfo.do', {'disclosureType': 'notice'}),
]

for url, params in post_urls:
    try:
        r = requests.post(url, data=params, headers=headers, timeout=5)
        print(f'POST {url}')
        print(f'  参数: {params}')
        print(f'  状态: {r.status_code}, 长度: {len(r.text)}')
        if r.status_code == 200 and len(r.text) > 100:
            try:
                data = r.json()
                print(f'  JSON键: {list(data.keys())[:5]}')
            except:
                pass
        print()
    except Exception as e:
        print(f'  错误: {e}\n')
