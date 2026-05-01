"""港交所公告搜索 - 探索隐藏API"""
import requests
import json
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.hkexnews.hk/',
}

# 先用prefix API获取stockId
def get_stock_id(code):
    """通过prefix API获取stockId"""
    url = 'https://www.hkexnews.hk/search/prefix.do'
    params = {
        'callback': 'callback',
        'lang': 'EN',
        'type': 'A',
        'name': code,
        'market': 'SEHK',
    }
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    # JSONP格式：callback({...})
    text = resp.text
    json_str = re.search(r'callback\((.*)\)', text, re.DOTALL)
    if json_str:
        data = json.loads(json_str.group(1))
        stocks = data.get('stockInfo', [])
        if stocks:
            return stocks[0].get('stockId'), stocks[0].get('name')
    return None, None

# 尝试各种可能的搜索API端点
def test_search_apis(code, stock_id, stock_name):
    print(f'\n=== {code} ({stock_name}) stockId={stock_id} ===\n')
    
    # 方案1: 直接搜索API（新版本可能已更换）
    search_endpoints = [
        # 从HKEX官网JS逆向的可能API
        {
            'name': 'search/titlesearch.xhtml (POST)',
            'url': 'https://www1.hkexnews.hk/search/titlesearch.xhtml',
            'method': 'POST',
            'data': {
                'searchStockCode': code,
                'stockId': str(stock_id),
                'market': 'SEHK',
                'searchType': '0',
                't1code': '-2',
                't2Gcode': '-2',
                't2code': '-2',
                'documentType': '-2',
                'from': '2024/01/01',
                'to': '2026/12/31',
                'title': '',
                'rowRange': '10',
                'startRow': '1',
            },
            'extra_headers': {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Faces-Request': 'partial/ajax',
            }
        },
        {
            'name': 'search/titlesearch.xhtml (POST, jsf)',
            'url': 'https://www1.hkexnews.hk/search/titlesearch.xhtml',
            'method': 'POST',
            'data': {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': 'j_idt10:j_idt14',
                'javax.faces.partial.execute': 'j_idt10:j_idt14',
                'javax.faces.partial.render': 'result',
                'j_idt10:j_idt14': 'j_idt10:j_idt14',
                'j_idt10': 'j_idt10',
                'j_idt10:searchStockCode': code,
                'j_idt10:stockId': str(stock_id),
                'j_idt10:searchType': '0',
                'j_idt10:t1code': '-2',
                'j_idt10:t2Gcode': '-2',
                'j_idt10:t2code': '-2',
                'j_idt10:documentType': '-2',
                'j_idt10:from': '2024/01/01',
                'j_idt10:to': '2026/12/31',
                'j_idt10:title': '',
                'j_idt10:rowRange': '10',
                'j_idt10:startRow': '1',
            },
            'extra_headers': {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Faces-Request': 'partial/ajax',
            }
        },
        # API v2 探测
        {
            'name': 'hkexnews/api/search (GET)',
            'url': f'https://www1.hkexnews.hk/search/titlesearch.xhtml',
            'method': 'GET_SEARCH',
        },
        # 新的可能API
        {
            'name': 'search-ms/api (GET)',
            'url': 'https://www1.hkexnews.hk/search-ms/api/search',
            'method': 'GET',
            'params': {
                'q': code,
                'market': 'SEHK',
                'language': 'EN',
            }
        },
    ]
    
    for ep in search_endpoints:
        print(f'--- {ep["name"]} ---')
        try:
            req_headers = {**headers, **ep.get('extra_headers', {})}
            
            if ep['method'] == 'POST':
                resp = requests.post(ep['url'], data=ep.get('data', {}), headers=req_headers, timeout=15)
            elif ep['method'] == 'GET':
                resp = requests.get(ep['url'], params=ep.get('params', {}), headers=req_headers, timeout=15)
            elif ep['method'] == 'GET_SEARCH':
                # 先GET搜索页，提取ViewState
                resp0 = requests.get(ep['url'], headers=headers, timeout=15)
                print(f'  搜索页状态: {resp0.status_code}, 大小: {len(resp0.text)}')
                # 提取ViewState
                vs = re.search(r'javax\.faces\.ViewState.*?value="([^"]*)"', resp0.text)
                if vs:
                    print(f'  ViewState: {vs.group(1)[:60]}...')
                # 提取jsessionid
                jsid = re.search(r'jsessionid=([A-F0-9]+)', resp0.text)
                if jsid:
                    print(f'  jsessionid: {jsid.group(1)}')
                # 提取所有hidden input
                hidden = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"', resp0.text)
                print(f'  Hidden inputs: {len(hidden)}')
                for name, val in hidden[:10]:
                    print(f'    {name} = {val[:50]}')
                # 检查有无iframe
                iframes = re.findall(r'<iframe[^>]*src="([^"]*)"', resp0.text)
                if iframes:
                    print(f'  iframes: {iframes}')
                continue
            
            print(f'  状态: {resp.status_code}, 大小: {len(resp.text)}')
            
            # 检查是否有PDF链接
            pdf_count = len(re.findall(r'\.pdf', resp.text))
            print(f'  PDF引用: {pdf_count}')
            
            # 检查是否有stock信息
            if code in resp.text:
                code_count = resp.text.count(code)
                print(f'  代码{code}出现: {code_count}次')
            
            # 如果是XML/HTML，检查关键标记
            if '<partial-response>' in resp.text or '<update>' in resp.text:
                print('  ⭐ JSF partial-response!')
                # 尝试提取CDATA内容
                cdata = re.findall(r'<!\[CDATA\[(.*?)\]\]>', resp.text, re.DOTALL)
                if cdata:
                    for i, cd in enumerate(cdata[:3]):
                        print(f'  CDATA[{i}]: {cd[:200]}')
                # 提取PDF链接
                pdfs = re.findall(r'href="([^"]*\.pdf)"', resp.text)
                if pdfs:
                    print(f'  ⭐ 找到PDF: {pdfs[:5]}')
            
            # 如果是JSON
            try:
                j = resp.json()
                print(f'  JSON keys: {list(j.keys())[:10]}')
                if 'result' in j:
                    print(f'  result: {str(j["result"])[:200]}')
            except:
                pass
                
        except Exception as e:
            print(f'  错误: {e}')
        print()

# 主测试
for code in ['00700', '09988']:
    stock_id, stock_name = get_stock_id(code)
    if stock_id:
        test_search_apis(code, stock_id, stock_name)
    else:
        print(f'{code}: 未找到stockId')
