"""港交所公告搜索 - Playwright监听网络请求"""
from playwright.sync_api import sync_playwright
import time
import re
import json

def search_hkex(stock_code, max_results=10):
    """使用Playwright搜索港交所公告，监听AJAX请求"""
    
    captured_responses = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 监听所有响应
        def handle_response(response):
            url = response.url
            if 'titlesearch' in url or 'search' in url.lower():
                try:
                    body = response.text()
                    captured_responses.append({
                        'url': url[:100],
                        'status': response.status,
                        'size': len(body),
                        'body': body[:2000],
                    })
                except:
                    pass
        
        page.on('response', handle_response)
        
        # 1. 访问搜索页
        url = 'https://www1.hkexnews.hk/search/titlesearch.xhtml'
        print(f'访问: {url}')
        page.goto(url, timeout=30000)
        page.wait_for_load_state('networkidle')
        time.sleep(3)
        
        # 2. 在输入框中输入股票代码（模拟真实打字）
        input_elem = page.locator('#searchStockCode')
        input_elem.click()
        time.sleep(0.5)
        
        # 逐字符输入触发自动补全
        for char in stock_code:
            input_elem.type(char, delay=100)
        
        time.sleep(3)  # 等待自动补全
        
        # 截图
        page.screenshot(path='hkex_autocomplete.png')
        
        # 3. 检查自动补全下拉列表
        dropdown_items = page.locator('.ui-autocomplete .ui-menu-item, .ui-corner-all, [class*="autocomplete"]').all()
        print(f'自动补全项: {len(dropdown_items)}')
        
        if dropdown_items:
            # 点击第一个匹配项
            for item in dropdown_items[:5]:
                try:
                    text = item.inner_text()
                    if stock_code in text or 'TENCENT' in text.upper():
                        print(f'选择: {text[:50]}')
                        item.click()
                        time.sleep(1)
                        break
                except:
                    continue
        else:
            # 尝试按Enter
            input_elem.press('Enter')
            time.sleep(2)
        
        # 4. 点击搜索按钮
        # 找所有按钮
        buttons = page.locator('button, input[type="submit"], input[type="button"]').all()
        print(f'按钮数: {len(buttons)}')
        for btn in buttons:
            try:
                text = btn.inner_text() or btn.get_attribute('value') or ''
                print(f'  Button: {text[:30]}, visible={btn.is_visible()}')
            except:
                pass
        
        # 尝试点击搜索
        try:
            page.locator('button:has-text("Search")').first.click(timeout=3000)
            print('点击Search按钮')
        except:
            # 试试其他方式
            try:
                page.locator('#searchBtn').first.click(timeout=3000)
                print('点击searchBtn')
            except:
                # 直接按Enter
                input_elem.press('Enter')
                print('按Enter搜索')
        
        # 等待结果
        time.sleep(8)
        page.screenshot(path='hkex_results.png')
        
        # 5. 分析捕获的响应
        print(f'\n捕获到 {len(captured_responses)} 个搜索相关响应:')
        for resp in captured_responses:
            print(f'  URL: {resp["url"]}')
            print(f'  Status: {resp["status"]}, Size: {resp["size"]}')
            
            # 检查是否有PDF
            pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', resp.get('body', ''))
            if pdfs:
                print(f'  ⭐ PDFs: {len(pdfs)}')
                for pdf in pdfs[:5]:
                    print(f'    {pdf[:80]}')
            
            # 检查是否有公告标题
            if '<td' in resp.get('body', ''):
                titles = re.findall(r'<td[^>]*>([^<]{10,})</td>', resp['body'])
                if titles:
                    print(f'  ⭐ Titles: {len(titles)}')
                    for t in titles[:5]:
                        print(f'    {t.strip()[:60]}')
        
        # 6. 从最终页面内容提取
        content = page.content()
        pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', content)
        real_pdfs = [p for p in set(pdfs) if '/sehk/' in p or 'listedco' in p]
        print(f'\n最终页面: {len(set(pdfs))} PDF, {len(real_pdfs)} 公告PDF')
        for p in real_pdfs[:max_results]:
            print(f'  {p[:80]}')
        
        browser.close()
        return real_pdfs

# 测试
results = search_hkex('00700')
