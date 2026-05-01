"""港交所搜索 - Playwright完整交互流程，捕获网络请求"""
from playwright.sync_api import sync_playwright
import time
import json
import re

def search_hkex_playwright(stock_code='00700'):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 捕获所有网络请求
        ajax_requests = []
        def handle_request(request):
            if request.method == 'POST' and 'titlesearch' in request.url:
                ajax_requests.append({
                    'url': request.url[:150],
                    'method': request.method,
                    'post_data': request.post_data[:3000] if request.post_data else '',
                    'headers': dict(list(request.headers.items())[:10]),
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
        
        # 1. 加载搜索页
        print('=== Step 1: 加载搜索页 ===')
        page.goto('https://www1.hkexnews.hk/search/titlesearch.xhtml', timeout=30000)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # 2. 接受Cookie
        try:
            accept_btn = page.locator('button:has-text("Accept"), a:has-text("Accept"), .btn-accept').first
            accept_btn.click(timeout=3000)
            time.sleep(0.5)
            print('Cookie已接受')
        except:
            print('无Cookie弹窗')
        
        # 3. 等待搜索面板加载
        print('\n=== Step 2: 等待搜索面板 ===')
        try:
            page.wait_for_selector('#searchStockCode', timeout=10000)
            print('搜索输入框已加载')
        except:
            print('搜索输入框超时')
        
        # 4. 输入股票代码
        print(f'\n=== Step 3: 输入 {stock_code} ===')
        input_elem = page.locator('#searchStockCode')
        input_elem.click()
        time.sleep(0.5)
        input_elem.fill('')  # 清空
        for char in stock_code:
            input_elem.type(char, delay=100)
        time.sleep(3)  # 等待自动补全
        
        # 5. 选择自动补全项
        print('\n=== Step 4: 选择自动补全 ===')
        try:
            page.wait_for_selector('.autocomplete-suggestion', timeout=5000)
            items = page.locator('.autocomplete-suggestion').all()
            print(f'自动补全项数: {len(items)}')
            for item in items:
                text = item.inner_text().strip()
                print(f'  - {text[:50]}')
                if stock_code in text:
                    item.click()
                    print(f'  已选择: {text.strip()[:50]}')
                    break
        except Exception as e:
            print(f'自动补全失败: {e}')
            # 尝试直接输入
            input_elem.fill(stock_code)
            time.sleep(2)
        
        time.sleep(1)
        
        # 6. 查找所有按钮和可点击元素
        print('\n=== Step 5: 查找可点击元素 ===')
        clickable = page.evaluate('''() => {
            const elements = document.querySelectorAll('button, input[type="submit"], input[type="button"], a[onclick], [role="button"]');
            return Array.from(elements).map(e => ({
                tag: e.tagName,
                id: e.id,
                name: e.name,
                value: e.value || '',
                text: e.textContent?.trim()?.substring(0, 40) || '',
                type: e.type || '',
                className: e.className?.substring(0, 60) || '',
                onclick: e.getAttribute('onclick')?.substring(0, 200) || '',
                visible: e.offsetParent !== null,
            }));
        }''')
        print(f'可点击元素数: {len(clickable)}')
        for elem in clickable:
            if elem.get('visible') and elem.get('text'):
                print(f"  {elem['tag']} id={elem['id'][:30]} text={elem['text'][:30]} type={elem['type']}")
        
        # 7. 查找搜索栏区域的所有元素
        print('\n=== Step 6: 搜索栏元素 ===')
        search_bar_elems = page.evaluate('''() => {
            const bar = document.querySelector('.title-search-search-bar');
            if (!bar) return 'no search bar';
            const all = bar.querySelectorAll('*');
            return Array.from(all).filter(e => e.id || e.className).slice(0, 40).map(e => ({
                tag: e.tagName,
                id: e.id?.substring(0, 40),
                className: e.className?.substring(0, 60) || '',
                type: e.type || '',
                text: e.textContent?.trim()?.substring(0, 30) || '',
                visible: e.offsetParent !== null,
            }));
        }''')
        if isinstance(search_bar_elems, list):
            for elem in search_bar_elems:
                if elem.get('visible'):
                    print(f"  {elem['tag']} id={elem['id']} class={elem['className'][:40]} text={elem['text'][:20]}")
        
        # 8. 查找搜索按钮 - 可能在filter区域内
        print('\n=== Step 7: Filter区域按钮 ===')
        filter_btns = page.evaluate('''() => {
            const filters = document.querySelectorAll('.filter__btn-applyFilters-js, .filter__btn, .btn-apply, [class*="apply"], [class*="search-btn"], [class*="searchBtn"]');
            return Array.from(filters).map(e => ({
                tag: e.tagName,
                id: e.id?.substring(0, 40),
                className: e.className?.substring(0, 60),
                text: e.textContent?.trim()?.substring(0, 30),
                visible: e.offsetParent !== null,
                onclick: e.getAttribute('onclick')?.substring(0, 200) || '',
            }));
        }''')
        print(f'搜索/应用按钮数: {len(filter_btns)}')
        for btn in filter_btns:
            print(f"  {btn['tag']} id={btn['id']} class={btn['className'][:40]} text={btn['text']}")
        
        # 9. 关键：查看stockId是否被设置到DOM中
        print('\n=== Step 8: 检查stockId ===')
        stock_info = page.evaluate('''() => {
            const inputs = document.querySelectorAll('input');
            const stockInputs = [];
            for (const inp of inputs) {
                const name = inp.name || inp.id || '';
                const value = inp.value || '';
                if (name.includes('stock') || name.includes('Stock') || 
                    value.includes('7609') || value.includes('00700') ||
                    name.includes('searchType') || name.includes('category')) {
                    stockInputs.push({name: name.substring(0, 50), value: value.substring(0, 50), type: inp.type, id: inp.id?.substring(0, 30)});
                }
            }
            return stockInputs;
        }''')
        print(f'股票相关inputs: {json.dumps(stock_info, indent=2)}')
        
        # 10. 尝试点击"Apply Filters"或搜索按钮
        print('\n=== Step 9: 触发搜索 ===')
        
        # 先看看filter区域的按钮文本
        apply_btns = page.locator('.filter__btn-applyFilters-js, .btn-apply, [class*="applyFilters"]').all()
        print(f'Apply按钮数: {len(apply_btns)}')
        for i, btn in enumerate(apply_btns):
            try:
                text = btn.inner_text(timeout=2000)
                print(f'  Apply按钮{i}: text="{text.strip()[:30]}"')
            except:
                pass
        
        # 尝试通过JS直接搜索
        # 找到titleSearchSearchPanel.html加载的JS
        search_panel_js = page.evaluate('''() => {
            // 检查全局对象
            const globals = ['titleSearchApp', 'hkexApp', 'searchPanel', 'TitleSearch'];
            const found = {};
            for (const g of globals) {
                try { found[g] = typeof window[g] !== 'undefined'; } catch(e) { found[g] = false; }
            }
            return found;
        }''')
        print(f'全局搜索对象: {search_panel_js}')
        
        # 尝试通过selectStockByCode函数选择
        select_result = page.evaluate('''() => {
            // 查找autocomplete的select回调
            const ac = document.querySelector('.autocomplete-suggestions');
            if (ac) {
                // 模拟选择第一项
                const items = ac.querySelectorAll('.autocomplete-suggestion');
                return {itemCount: items.length, html: ac.innerHTML?.substring(0, 300)};
            }
            return 'no autocomplete';
        }''')
        print(f'自动补全状态: {select_result}')
        
        # 11. 最终手段：用page.keyboard模拟Tab+Enter
        print('\n=== Step 10: 键盘搜索 ===')
        # Tab到搜索按钮然后Enter
        input_elem.click()
        time.sleep(0.3)
        # 按Enter
        page.keyboard.press('Enter')
        time.sleep(3)
        
        # 检查结果
        print('\n=== Step 11: 检查搜索结果 ===')
        rows = page.locator('.title-search-result table tr, .table tbody tr').all()
        print(f'表格行数: {len(rows)}')
        
        pdf_links = page.locator('a[href*=".pdf"]').all()
        print(f'PDF链接数: {len(pdf_links)}')
        
        # 检查AJAX请求
        print(f'\n=== AJAX请求捕获: {len(ajax_requests)} ===')
        for req in ajax_requests:
            print(f"  POST {req['url'][-80:]}")
            print(f"  PostData: {req['post_data'][:500]}")
        
        print(f'\n=== AJAX响应捕获: {len(ajax_responses)} ===')
        for resp in ajax_responses[:3]:
            print(f"  {resp[:500]}")
        
        browser.close()

if __name__ == '__main__':
    search_hkex_playwright('00700')
