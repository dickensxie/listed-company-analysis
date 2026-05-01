"""港交所公告搜索 - 使用JS函数触发搜索"""
from playwright.sync_api import sync_playwright
import time
import re

def search_hkex(stock_code, max_results=20):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. 访问搜索页
        page.goto('https://www1.hkexnews.hk/search/titlesearch.xhtml', timeout=30000)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # 2. 接受Cookie
        try:
            page.locator('button:has-text("Accept")').first.click(timeout=3000)
            time.sleep(1)
        except:
            pass
        
        # 3. 输入股票代码 + 选择自动补全
        input_elem = page.locator('#searchStockCode')
        input_elem.click()
        time.sleep(0.3)
        
        for char in stock_code:
            input_elem.type(char, delay=80)
        time.sleep(3)
        
        # 选择自动补全
        try:
            page.wait_for_selector('.autocomplete-suggestion', timeout=5000)
            items = page.locator('.autocomplete-suggestion').all()
            for item in items:
                try:
                    text = item.inner_text()
                    if stock_code in text:
                        item.click()
                        print(f'已选择: {text.strip()[:50]}')
                        break
                except:
                    continue
        except:
            print('自动补全超时')
        
        time.sleep(1)
        
        # 4. 检查stockId
        stock_id = page.locator('input[name="stockId"]').first.get_attribute('value') or ''
        print(f'stockId: {stock_id}')
        
        # 5. 设置搜索类型为0（全部）
        page.evaluate('() => setSearchType(0)')
        time.sleep(0.5)
        
        # 6. 触发搜索 - 使用正确的JS函数
        # route_lci_app_search 是主搜索函数
        print('调用 route_lci_app_search()...')
        
        # 先设置搜索参数
        page.evaluate('''() => {
            // 设置stockId
            document.querySelector('input[name="stockId"]').value = '%s';
            // 设置from/to日期
            document.querySelector('input[name="from"]').value = '20240101';
            document.querySelector('input[name="to"]').value = '20261231';
            // 设置searchType
            document.querySelector('input[name="searchType"]').value = '0';
            // 设置documentType
            document.querySelector('input[name="documentType"]').value = '-2';
        }''' % stock_id)
        
        time.sleep(0.5)
        
        # 调用搜索函数
        result = page.evaluate('''() => {
            try {
                route_lci_app_search();
                return "route_lci_app_search called";
            } catch(e) {
                return "route_lci_app_search error: " + e.message;
            }
        }''')
        print(f'搜索结果: {result}')
        
        # 7. 等待结果加载
        print('等待结果...')
        for attempt in range(15):
            time.sleep(2)
            
            # 检查是否有数据行
            result_text = page.locator('#searchResult, .search-result, .result-container, #resultTable').first.inner_text() if page.locator('#searchResult, .search-result, .result-container, #resultTable').count() > 0 else ''
            if result_text and len(result_text) > 20 and 'Release Time' not in result_text[:50]:
                print(f'  第{attempt+1}次: 找到结果!')
                break
            print(f'  第{attempt+1}次: 等待中...')
        
        time.sleep(3)
        
        # 8. 提取结果
        content = page.content()
        
        # 从所有a标签提取PDF
        all_links = page.locator('a').all()
        announcements = []
        seen = set()
        
        for link in all_links:
            try:
                href = link.get_attribute('href') or ''
                text = link.inner_text().strip()
                
                # 只要包含/sehk/的PDF链接
                if '/sehk/' in href and href not in seen:
                    seen.add(href)
                    announcements.append({
                        'title': text[:100] if text else '(untitled)',
                        'url': href if href.startswith('http') else f'https://www1.hkexnews.hk{href}',
                    })
            except:
                continue
        
        # 汇总
        print(f'\n===== 港交所公告: {stock_code} =====')
        print(f'公告数: {len(announcements)}')
        
        for a in announcements[:max_results]:
            print(f'  {a["title"][:70]}')
            print(f'    → {a["url"][:80]}')
        
        if not announcements:
            # 调试：检查页面URL是否变化了
            print(f'\n当前URL: {page.url}')
            print('尝试getTitleSearchCriteria:')
            criteria = page.evaluate('''() => {
                try {
                    return JSON.stringify(getTitleSearchCriteria());
                } catch(e) {
                    return "error: " + e.message;
                }
            }''')
            print(f'  {criteria}')
        
        page.screenshot(path='hkex_final_v6.png')
        browser.close()
        return announcements

search_hkex('00700')
