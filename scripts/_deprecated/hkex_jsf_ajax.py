"""港交所JSF AJAX搜索 - 模拟浏览器的JSF部分提交"""
import requests
from bs4 import BeautifulSoup
import re
import json
import time

BASE = 'https://www1.hkexnews.hk'

def search_hkex(stock_code='00700'):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    
    # Step 1: 获取搜索页面，提取ViewState和jsessionid
    print('=== Step 1: 加载搜索页 ===')
    r = session.get(f'{BASE}/search/titlesearch.xhtml', timeout=30)
    print(f'Status: {r.status_code}, Size: {len(r.text)}')
    
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # 提取ViewState
    vs_input = soup.find('input', {'name': 'javax.faces.ViewState'})
    view_state = vs_input['value'] if vs_input else ''
    print(f'ViewState: {view_state[:50]}...')
    
    # 提取jsessionid (从URL或cookie)
    jsessionid = ''
    for cookie in session.cookies:
        if 'JSESSIONID' in cookie.name.upper() or 'jsessionid' in cookie.name.lower():
            jsessionid = cookie.value
            print(f'JSESSIONID cookie: {jsessionid[:30]}...')
    
    # 从form action提取jsessionid
    form = soup.find('form')
    if form and form.get('action'):
        action = form['action']
        jid_match = re.search(r'jsessionid=([A-Za-z0-9_.]+)', action)
        if jid_match:
            jsessionid = jid_match.group(1)
            print(f'JSESSIONID from form: {jsessionid[:30]}...')
    
    # 提取所有hidden inputs
    hidden_inputs = {}
    for inp in soup.find_all('input', {'type': 'hidden'}):
        name = inp.get('name', '')
        value = inp.get('value', '')
        if name:
            hidden_inputs[name] = value
            print(f'  Hidden: {name} = {value[:50]}')
    
    # 找form id
    form_id = form.get('id', '') if form else ''
    print(f'Form ID: {form_id}')
    
    # Step 2: 获取stockId (通过prefix API)
    print('\n=== Step 2: 获取stockId ===')
    prefix_url = f'https://www.hkexnews.hk/search/prefix.do'
    prefix_params = {
        'callback': 'callback',
        'lang': 'EN',
        'type': 'A',
        'name': stock_code,
        'market': 'SEHK',
    }
    r2 = session.get(prefix_url, params=prefix_params, timeout=10)
    print(f'Prefix API: {r2.status_code}, {len(r2.text)} bytes')
    
    # 解析JSONP
    json_str = re.search(r'callback\((.*)\)', r2.text, re.DOTALL)
    stock_id = ''
    stock_name = ''
    if json_str:
        try:
            data = json.loads(json_str.group(1))
            if data.get('stockInfo'):
                for si in data['stockInfo']:
                    if si.get('code') == stock_code:
                        stock_id = str(si.get('stockId', ''))
                        stock_name = si.get('name', '')
                        break
            print(f'Stock: {stock_code} {stock_name}, ID: {stock_id}')
        except:
            print(f'JSON parse error: {json_str.group(1)[:200]}')
    
    if not stock_id:
        print('未找到stockId，退出')
        return
    
    # Step 3: JSF AJAX请求 - 搜索
    print('\n=== Step 3: JSF AJAX搜索 ===')
    
    # JSF AJAX请求需要特定的请求头
    ajax_headers = {
        'Faces-Request': 'partial/ajax',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'application/xml, text/xml, */*; q=0.01',
        'Origin': BASE,
        'Referer': f'{BASE}/search/titlesearch.xhtml',
    }
    session.headers.update(ajax_headers)
    
    # 构造JSF AJAX POST body
    # 尝试不同的Source按钮（搜索按钮可能是j_idt12:j_idt40之类）
    # 先用搜索面板的form
    
    # 方案A: 模拟搜索按钮点击
    # javax.faces.Source 指定触发事件的组件
    # 尝试常见的搜索按钮ID
    
    possible_sources = [
        f'{form_id}:searchBtn',
        f'{form_id}:btnSearch',
        f'{form_id}:j_idt40',
        f'{form_id}:j_idt42',
        'j_idt12:j_idt40',
        'j_idt12:j_idt42',
        'j_idt12:searchBtn',
    ]
    
    for source in possible_sources:
        print(f'\n--- 尝试 Source: {source} ---')
        
        data = {
            source: source,  # 按钮值
            'javax.faces.ViewState': view_state,
            'javax.faces.source': source,
            'javax.faces.partial.execute': f'{source} @all',
            'javax.faces.partial.render': f'{form_id}:resultPanel @all',
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.event': 'click',
            # 股票相关参数
            f'{form_id}:stockId': stock_id,
            f'{form_id}:stockCode': stock_code,
            f'{form_id}:searchType': '0',
            f'{form_id}:searchTypeInt': '0',
            # 日期范围
            f'{form_id}:from': '20240101',
            f'{form_id}:to': '20260427',
            # category
            f'{form_id}:category': '0',
            # tier1
            f'{form_id}:tier1-select': '0',
        }
        
        # 也添加所有hidden inputs
        for k, v in hidden_inputs.items():
            if k not in data and k != 'javax.faces.ViewState':
                data[k] = v
        
        try:
            r3 = session.post(
                f'{BASE}/search/titlesearch.xhtml',
                data=data,
                timeout=15
            )
            print(f'Status: {r3.status_code}, Size: {len(r3.text)}')
            
            # 检查是否是JSF partial-response
            if '<partial-response>' in r3.text or '<changes>' in r3.text:
                print('✅ 收到JSF partial-response!')
                # 提取结果
                if 'pdf' in r3.text.lower() or 'document' in r3.text.lower():
                    print('包含文档链接!')
                print(r3.text[:1000])
                break
            elif r3.text.strip().startswith('<'):
                print(f'响应类型: XML/HTML, 前200字符: {r3.text[:200]}')
            else:
                print(f'响应类型: 未知, 前200字符: {r3.text[:200]}')
                
        except Exception as e:
            print(f'请求错误: {e}')
    
    # Step 4: 尝试不带Source的纯表单提交
    print('\n=== Step 4: 纯表单POST (非AJAX) ===')
    session.headers.pop('Faces-Request', None)
    session.headers.pop('X-Requested-With', None)
    session.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    session.headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    form_data = {}
    for k, v in hidden_inputs.items():
        form_data[k] = v
    form_data.update({
        f'{form_id}:stockId': stock_id,
        f'{form_id}:stockCode': stock_code,
        f'{form_id}:searchType': '0',
        f'{form_id}:searchTypeInt': '0',
        f'{form_id}:category': '0',
        f'{form_id}:from': '20240101',
        f'{form_id}:to': '20260427',
        'javax.faces.ViewState': view_state,
    })
    
    r4 = session.post(f'{BASE}/search/titlesearch.xhtml', data=form_data, timeout=15)
    print(f'Status: {r4.status_code}, Size: {len(r4.text)}')
    
    # 检查结果
    soup4 = BeautifulSoup(r4.text, 'html.parser')
    # 找表格
    table = soup4.find('table', class_=re.compile(r'table|result'))
    if table:
        rows = table.find_all('tr')
        print(f'表格行数: {len(rows)}')
        for row in rows[:5]:
            cells = row.find_all(['td', 'th'])
            print('  | '.join(c.get_text(strip=True)[:30] for c in cells))
    else:
        # 检查PDF链接
        pdf_links = soup4.find_all('a', href=re.compile(r'\.pdf', re.I))
        print(f'PDF链接数: {len(pdf_links)}')
        if pdf_links:
            for link in pdf_links[:5]:
                print(f'  {link.get("href", "")[:80]}')
        
        # 检查stockId是否在结果中
        if stock_code in r4.text or stock_name in r4.text:
            print(f'✅ 在响应中找到 {stock_code}/{stock_name}!')
        else:
            print('响应中未找到股票信息')

    # Step 5: 尝试HKEX公开的搜索API（如果有）
    print('\n=== Step 5: HKEX搜索API探索 ===')
    api_urls = [
        f'https://www1.hkexnews.hk/ncms/json/eds/search_result_json.json?lang=EN&category=0&market=SEHK&stockId={stock_id}&from=20240101&to=20260427',
        f'https://www1.hkexnews.hk/search/titlesearch.xhtml?stockId={stock_id}&stockCode={stock_code}',
        f'https://www1.hkexnews.hk/app/appyearindex.html?searchkey={stock_code}',
    ]
    for url in api_urls:
        try:
            session.headers['Accept'] = 'application/json, text/javascript, */*'
            r5 = session.get(url, timeout=10)
            print(f'URL: ...{url[-60:]}')
            print(f'  Status: {r5.status_code}, Size: {len(r5.text)}, Content: {r5.text[:200]}')
        except Exception as e:
            print(f'  Error: {e}')

if __name__ == '__main__':
    search_hkex('00700')
