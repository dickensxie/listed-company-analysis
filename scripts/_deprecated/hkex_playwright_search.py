"""港交所公告搜索 - Playwright方案"""
from playwright.sync_api import sync_playwright
import time
import re

def search_hkex_announcements(stock_code, max_results=10):
    """使用Playwright搜索港交所公告"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. 访问搜索页
        url = 'https://www1.hkexnews.hk/search/titlesearch.xhtml'
        print(f'访问搜索页: {url}')
        page.goto(url, timeout=30000)
        page.wait_for_load_state('networkidle')
        time.sleep(3)
        
        # 2. 截图看看页面状态
        page.screenshot(path='hkex_search_initial.png')
        print(f'页面标题: {page.title()}')
        
        # 3. 找到股票代码输入框并输入
        # 尝试多种选择器
        selectors = [
            'input#stockCode',
            'input[name*="stockCode"]',
            'input.search-input',
            'input[type="text"]',
            '#searchStockCode',
        ]
        
        input_found = False
        for sel in selectors:
            try:
                elem = page.locator(sel).first
                if elem.is_visible(timeout=2000):
                    print(f'找到输入框: {sel}')
                    elem.click()
                    elem.fill(stock_code)
                    input_found = True
                    time.sleep(2)  # 等待自动补全
                    
                    # 检查是否出现了下拉列表
                    page.screenshot(path='hkex_search_typed.png')
                    break
            except:
                continue
        
        if not input_found:
            print('未找到股票输入框，尝试点击搜索区域')
            # 可能需要先点击搜索类型
            try:
                # 点击"按股票代码搜索"
                page.locator('text=Stock Code').first.click(timeout=3000)
                time.sleep(1)
                page.screenshot(path='hkex_search_click_stock.png')
            except:
                pass
        
        # 4. 等待自动补全出现并选择
        try:
            # 等待下拉列表
            autocomplete = page.locator('.ui-autocomplete-item, .autocomplete-item, .dropdown-item, li.ui-menu-item').first
            autocomplete.click(timeout=5000)
            print('选择了自动补全结果')
            time.sleep(1)
        except:
            print('无自动补全，尝试直接搜索')
        
        # 5. 点击搜索按钮
        button_selectors = [
            'button:has-text("Search")',
            'input[type="submit"]',
            'button.search-btn',
            '#searchBtn',
            '.btn-search',
        ]
        
        for sel in button_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    print(f'点击搜索按钮: {sel}')
                    btn.click()
                    time.sleep(5)  # 等待结果加载
                    page.screenshot(path='hkex_search_results.png')
                    break
            except:
                continue
        
        # 6. 提取结果
        # 等待结果表格
        try:
            page.wait_for_selector('.result-table, table, .search-result, #result', timeout=10000)
        except:
            print('等待结果超时')
        
        # 获取页面内容
        content = page.content()
        
        # 提取PDF链接
        pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', content)
        pdfs = list(set(pdfs))
        # 过滤出真实公告PDF
        real_pdfs = [p for p in pdfs if '/sehk/' in p or 'listedco' in p]
        
        print(f'\n找到 {len(pdfs)} 个PDF链接，其中 {len(real_pdfs)} 个公告PDF')
        
        # 提取公告标题
        # 尝试从表格行提取
        rows = page.locator('tr').all()
        print(f'表格行数: {len(rows)}')
        
        announcements = []
        for row in rows[:30]:
            try:
                text = row.inner_text()
                links = row.locator('a').all()
                for link in links:
                    href = link.get_attribute('href') or ''
                    title = link.inner_text().strip()
                    if '.pdf' in href and title:
                        announcements.append({
                            'title': title[:100],
                            'url': href if href.startswith('http') else f'https://www1.hkexnews.hk{href}',
                        })
            except:
                continue
        
        print(f'\n公告数: {len(announcements)}')
        for a in announcements[:max_results]:
            print(f'  {a["title"][:60]}')
            print(f'    {a["url"][:80]}')
        
        browser.close()
        return announcements

# 测试
results = search_hkex_announcements('00700')
