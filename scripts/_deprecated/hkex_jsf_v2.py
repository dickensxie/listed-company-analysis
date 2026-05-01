"""港交所公告搜索 - 正确JSF交互"""
import requests, re, json

headers_base = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

def search_hkex(stock_code):
    """通过JSF搜索港交所公告"""
    
    # 1. GET搜索页 - 获取ViewState和jsessionid
    search_url = 'https://www1.hkexnews.hk/search/titlesearch.xhtml'
    resp0 = requests.get(search_url, headers=headers_base, timeout=15)
    print(f'搜索页: {resp0.status_code}, {len(resp0.text)} bytes')
    
    # 提取ViewState
    vs_match = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]*)"', resp0.text)
    view_state = vs_match.group(1) if vs_match else ''
    print(f'ViewState: {view_state[:40]}...')
    
    # 提取form action (含jsessionid)
    form_match = re.search(r'action="([^"]*jsessionid=[^"]*)"', resp0.text)
    form_action = form_match.group(1) if form_match else '/search/titlesearch.xhtml'
    print(f'Form action: {form_action[:80]}...')
    
    # 从prefix API获取stockId
    prefix_url = 'https://www.hkexnews.hk/search/prefix.do'
    params = {'callback': 'cb', 'lang': 'EN', 'type': 'A', 'name': stock_code, 'market': 'SEHK'}
    prefix_resp = requests.get(prefix_url, params=params, headers=headers_base, timeout=10)
    json_match = re.search(r'cb\((.*)\)', prefix_resp.text, re.DOTALL)
    stock_id = ''
    stock_name = ''
    if json_match:
        pdata = json.loads(json_match.group(1))
        stocks = pdata.get('stockInfo', [])
        if stocks:
            stock_id = str(stocks[0].get('stockId', ''))
            stock_name = stocks[0].get('name', '')
    print(f'Stock: {stock_name} ({stock_code}), ID: {stock_id}')
    
    # 2. 构建JSF AJAX POST - 使用正确的form id (j_idt12)
    # 搜索按钮的clientId需要从页面分析得出
    # 尝试多种可能的搜索触发源
    search_sources = [
        'j_idt12:j_idt20',  # 常见模式
        'j_idt12:j_idt22',
        'j_idt12:j_idt24',
        'j_idt12:searchBtn',
        'j_idt12:btnSearch',
    ]
    
    full_url = f'https://www1.hkexnews.hk{form_action}'
    
    for source in search_sources:
        post_data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': source,
            'javax.faces.partial.execute': source,
            'javax.faces.partial.render': 'titleSearchResultControl',
            source: source,
            'j_idt12': 'j_idt12',
            'j_idt12:loadMoreRange': '100',
            # 设置搜索参数 - 通过hidden input的name
            'j_idt12:stockId': stock_id,
            'j_idt12:stockCode': stock_code,
            'j_idt12:searchType': '0',
            'j_idt12:searchTypeInt': '0',
            'j_idt12:newsTitle': '',
            'j_idt12:tierOneId': '-2',
            'j_idt12:tierTwoGpId': '-2',
            'j_idt12:tierTwoId': '-2',
            'j_idt12:selectedDocType': '-2',
            'j_idt12:startDate': '20240101',
            'j_idt12:endDate': '20261231',
            'j_idt12:selectedSecurities': '',
            'j_idt12:displayResultTable': 'block',
            'javax.faces.ViewState': view_state,
            'titleSearchResultControl.searchByIndex': '0',
        }
        
        ajax_headers = {
            **headers_base,
            'Accept': 'application/xml, text/xml, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Faces-Request': 'partial/ajax',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': search_url,
        }
        
        try:
            resp1 = requests.post(full_url, data=post_data, headers=ajax_headers, timeout=15)
            pdf_count = len(re.findall(r'\.pdf', resp1.text))
            
            # 检查是否有有意义的结果
            if pdf_count > 0 or len(resp1.text) > 500:
                print(f'\n⭐ Source={source}: Status={resp1.status_code}, Size={len(resp1.text)}, PDFs={pdf_count}')
                
                # 解析结果
                if '<partial-response>' in resp1.text:
                    # 提CDATA
                    cdatas = re.findall(r'<!\[CDATA\[(.*?)\]\]>', resp1.text, re.DOTALL)
                    for cd in cdatas:
                        if len(cd) > 100:
                            # 查找公告标题
                            titles = re.findall(r'<a[^>]*>([^<]{10,})</a>', cd)
                            if titles:
                                print(f'  标题数: {len(titles)}')
                                for t in titles[:5]:
                                    print(f'  - {t.strip()[:80]}')
                            
                            pdfs = re.findall(r'href="([^"]*\.pdf)"', cd)
                            if pdfs:
                                print(f'  PDFs: {len(pdfs)}')
                                for p in pdfs[:5]:
                                    print(f'  - {p[:80]}')
                else:
                    print(resp1.text[:300])
                return  # 找到了就退出
            else:
                print(f'  Source={source}: Size={len(resp1.text)}, 无结果')
        except Exception as e:
            print(f'  Source={source}: Error={e}')
    
    # 3. 如果所有source都失败，尝试简单POST不带AJAX
    print('\n--- 尝试普通POST（非AJAX）---')
    post_data2 = {
        'j_idt12': 'j_idt12',
        'j_idt12:loadMoreRange': '100',
        'j_idt12:stockId': stock_id,
        'j_idt12:stockCode': stock_code,
        'j_idt12:searchType': '0',
        'j_idt12:searchTypeInt': '0',
        'j_idt12:newsTitle': '',
        'j_idt12:tierOneId': '-2',
        'j_idt12:tierTwoGpId': '-2',
        'j_idt12:tierTwoId': '-2',
        'j_idt12:selectedDocType': '-2',
        'j_idt12:startDate': '20240101',
        'j_idt12:endDate': '20261231',
        'javax.faces.ViewState': view_state,
        'titleSearchResultControl.searchByIndex': '0',
    }
    
    resp2 = requests.post(full_url, data=post_data2, headers=headers_base, timeout=15)
    pdf_count = len(re.findall(r'\.pdf', resp2.text))
    print(f'普通POST: Status={resp2.status_code}, Size={len(resp2.text)}, PDFs={pdf_count}')
    
    if pdf_count > 0:
        pdfs = re.findall(r'href="([^"]*\.pdf)"', resp2.text)
        for p in pdfs[:10]:
            print(f'  {p[:100]}')

# 测试
search_hkex('00700')
