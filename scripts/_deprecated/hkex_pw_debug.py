"""港交所公告搜索 - 监听JSF请求+触发搜索"""
from playwright.sync_api import sync_playwright
import time
import re
import json

def search_hkex(stock_code, max_results=20):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 监听所有请求和响应
        ajax_data = []
        def handle_request(request):
            if request.method == 'POST' and 'titlesearch' in request.url:
                ajax_data.append({
                    'type': 'request',
                    'url': request.url[:100],
                    'method': request.method,
                    'post_data': request.post_data[:2000] if request.post_data else '',
                })
        
        ajax_responses = []
        def handle_response(response):
            if 'titlesearch' in response.url and response.request.method == 'POST':
                try:
                    body = response.text()
                    ajax_responses.append(body[:5000])
                except:
                    pass
        
        page.on('request', handle_request)
        page.on('response', handle_response)
        
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
        
        # 3. 等待搜索面板加载
        try:
            page.wait_for_selector('#searchStockCode', timeout=10000)
        except:
            pass
        
        # 4. 输入股票代码并选择
        input_elem = page.locator('#searchStockCode')
        input_elem.click()
        time.sleep(0.3)
        
        for char in stock_code:
            input_elem.type(char, delay=80)
        time.sleep(3)
        
        try:
            page.wait_for_selector('.autocomplete-suggestion', timeout=5000)
            items = page.locator('.autocomplete-suggestion').all()
            for item in items:
                text = item.inner_text()
                if stock_code in text:
                    item.click()
                    print(f'已选择: {text.strip()[:50]}')
                    break
        except:
            print('自动补全超时')
        
        time.sleep(1)
        
        # 5. 使用JSF方式触发搜索
        # 获取当前ViewState
        view_state = page.evaluate('() => document.querySelector("input[name=\'javax.faces.ViewState\']").value')
        print(f'ViewState: {view_state[:40]}...')
        
        # 查找搜索按钮的clientId
        # 在JSF中，搜索按钮通常是commandButton或commandLink
        # 查找所有submit/input按钮
        buttons_info = page.evaluate('''() => {
            const buttons = document.querySelectorAll('input[type="submit"], button[type="submit"], a[onclick*="ajax"]');
            return Array.from(buttons).map(b => ({
                id: b.id,
                name: b.name,
                value: b.value || b.textContent,
                className: b.className,
                onclick: b.getAttribute('onclick')?.substring(0, 200) || '',
            }));
        }''')
        print(f'\n搜索按钮候选: {json.dumps(buttons_info, indent=2)}')
        
        # 6. 直接点击搜索面板中的搜索按钮
        # 搜索面板在 #searchPanel 区域，搜索按钮可能在里面
        # 用evaluate查找搜索面板中的按钮
        search_panel_buttons = page.evaluate('''() => {
            const panel = document.getElementById('searchPanel') || document.querySelector('.search-panel');
            if (!panel) return 'no panel found';
            const btns = panel.querySelectorAll('input[type="submit"], button, a[onclick]');
            return Array.from(btns).map(b => ({
                tag: b.tagName,
                id: b.id,
                name: b.name,
                value: b.value || b.textContent?.trim()?.substring(0, 30),
                className: b.className?.substring(0, 50),
                onclick: b.getAttribute('onclick')?.substring(0, 200) || '',
            }));
        }''')
        print(f'\n搜索面板按钮: {json.dumps(search_panel_buttons, indent=2)}')
        
        # 7. 尝试查找整个页面中的搜索相关按钮
        all_search_btns = page.evaluate('''() => {
            const all = document.querySelectorAll('[id*="search"], [id*="Search"], [class*="search"], [class*="Search"]');
            return Array.from(all).slice(0, 20).map(e => ({
                tag: e.tagName,
                id: e.id?.substring(0, 50),
                className: e.className?.substring(0, 50),
                type: e.type,
                text: e.textContent?.trim()?.substring(0, 30),
            }));
        }''')
        print(f'\n搜索相关元素: {json.dumps(all_search_btns, indent=2)}')
        
        # 8. 最简单的方式：模拟JSF搜索按钮点击
        # 从搜索面板HTML找到搜索触发的具体方式
        # 先看看搜索面板加载了什么HTML
        panel_html = page.evaluate('''() => {
            // 搜索面板可能直接在body中
            const content = document.querySelector('#searchPanel')?.innerHTML 
                         || document.querySelector('.title-search-section')?.innerHTML
                         || document.querySelector('.titlesearch-header-section')?.innerHTML
                         || 'not found';
            return content.substring(0, 3000);
        }''')
        print(f'\n搜索面板HTML（前3000字符）:')
        print(panel_html[:3000])
        
        browser.close()

search_hkex('00700')
