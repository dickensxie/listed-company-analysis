"""港交所公告搜索 - 完整JSF交互"""
import requests
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/xml, text/xml, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'X-Requested-With': 'XMLHttpRequest',
    'Faces-Request': 'partial/ajax',
}

def search_hkex_announcements(stock_code):
    """通过JSF搜索港交所公告"""
    
    # 1. 先GET搜索页，获取ViewState和jsessionid
    session = requests.Session()
    # 不全局设置headers，避免覆盖Accept
    
    search_url = 'https://www1.hkexnews.hk/search/titlesearch.xhtml'
    resp0 = session.get(search_url, headers=headers, timeout=15)
    print(f'搜索页: {resp0.status_code}, {len(resp0.text)} bytes')
    
    # 提取ViewState
    vs_match = re.search(r'name="javax\.faces\.ViewState"\s+value="([^"]*)"', resp0.text)
    if not vs_match:
        vs_match = re.search(r'id="javax\.faces\.ViewState"\s+value="([^"]*)"', resp0.text)
    view_state = vs_match.group(1) if vs_match else ''
    print(f'ViewState: {view_state[:40]}...')
    
    # 提取所有隐藏字段
    hidden_fields = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"', resp0.text):
        hidden_fields[m.group(1)] = m.group(2)
    print(f'Hidden fields: {list(hidden_fields.keys())}')
    
    # 从prefix API获取stockId
    prefix_url = 'https://www.hkexnews.hk/search/prefix.do'
    params = {'callback': 'cb', 'lang': 'EN', 'type': 'A', 'name': stock_code, 'market': 'SEHK'}
    prefix_resp = session.get(prefix_url, params=params, headers=headers, timeout=10)
    json_match = re.search(r'cb\((.*)\)', prefix_resp.text, re.DOTALL)
    if json_match:
        pdata = json.loads(json_match.group(1))
        stocks = pdata.get('stockInfo', [])
        stock_id = stocks[0].get('stockId') if stocks else ''
        stock_name = stocks[0].get('name', '') if stocks else ''
        print(f'Stock: {stock_name} ({stock_code}), ID: {stock_id}')
    else:
        stock_id = ''
        stock_name = ''
    
    # 2. 构建完整的JSF AJAX POST请求
    # 需要模拟搜索按钮点击
    post_data = {
        'javax.faces.partial.ajax': 'true',
        'javax.faces.source': 'j_idt10:j_idt14',  # 搜索按钮
        'javax.faces.partial.execute': 'j_idt10:j_idt14',
        'javax.faces.partial.render': 'result',
        'j_idt10:j_idt14': 'j_idt10:j_idt14',
        'j_idt10': 'j_idt10',
        'j_idt10:searchStockCode': stock_code,
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
        'javax.faces.ViewState': view_state,
    }
    
    # 添加隐藏字段
    for k, v in hidden_fields.items():
        if k not in post_data:
            post_data[k] = v
    
    post_headers = {**headers, 'Content-Type': 'application/x-www-form-urlencoded'}
    resp1 = session.post(search_url, data=post_data, 
                         headers=post_headers,
                         timeout=15)
    print(f'\n搜索结果: {resp1.status_code}, {len(resp1.text)} bytes')
    
    # 解析JSF partial response
    if '<partial-response>' in resp1.text:
        # 提取所有update块
        updates = re.findall(r'<update\s+id="([^"]*)">(.*?)</update>', resp1.text, re.DOTALL)
        print(f'Updates: {len(updates)}')
        
        for uid, content in updates:
            # 去掉CDATA标记
            content = re.sub(r'^<!\[CDATA\[', '', content)
            content = re.sub(r'\]\]>$', '', content)
            print(f'\n--- Update: {uid} ({len(content)} chars) ---')
            
            if len(content) > 50:
                # 查找PDF链接
                pdfs = re.findall(r'href="([^"]*\.pdf)"', content)
                if pdfs:
                    print(f'⭐ 找到 {len(pdfs)} 个PDF!')
                    for p in pdfs[:10]:
                        print(f'  {p}')
                
                # 查找公告标题
                titles = re.findall(r'<td[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</td>', content, re.DOTALL)
                if titles:
                    print(f'⭐ 找到 {len(titles)} 个标题!')
                    for t in titles[:10]:
                        clean = re.sub(r'<[^>]+>', '', t).strip()
                        if clean:
                            print(f'  {clean[:80]}')
                
                # 打印前500字符
                print(content[:500])
    else:
        # 可能返回了HTML
        pdfs = re.findall(r'href="([^"]*\.pdf)"', resp1.text)
        if pdfs:
            print(f'⭐ 找到 {len(pdfs)} 个PDF!')
            for p in pdfs[:10]:
                print(f'  {p}')
        else:
            print('无PDF链接')
            print(resp1.text[:500])

# 测试
search_hkex_announcements('00700')
