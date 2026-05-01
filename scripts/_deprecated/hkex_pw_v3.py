"""港交所公告搜索 - 处理Cookie弹窗+触发搜索"""
from playwright.sync_api import sync_playwright
import time
import re

def search_hkex(stock_code, max_results=10):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 监听AJAX响应
        ajax_responses = []
        def handle_response(response):
            url = response.url
            if 'titlesearch.xhtml' in url and response.request.method == 'POST':
                try:
                    body = response.text()
                    ajax_responses.append(body)
                except:
                    pass
        page.on('response', handle_response)
        
        # 1. 访问搜索页
        url = 'https://www1.hkexnews.hk/search/titlesearch.xhtml'
        page.goto(url, timeout=30000)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # 2. 处理Cookie同意弹窗
        try:
            accept_btn = page.locator('button:has-text("Accept")').first
            if accept_btn.is_visible(timeout=3000):
                accept_btn.click()
                print('已接受Cookie')
                time.sleep(1)
        except:
            print('无Cookie弹窗')
        
        # 3. 加载搜索面板（titleSearchSearchPanel.html）
        # 这是JSF动态加载的搜索面板
        # 等待搜索面板加载
        try:
            page.wait_for_selector('#searchStockCode', timeout=10000)
            print('搜索面板已加载')
        except:
            print('等待搜索面板超时，尝试直接加载')
            # 手动触发加载
            page.evaluate('$.get("/search/titleSearchSearchPanel.html", function(d){$("#searchPanel").html(d)})')
            time.sleep(3)
        
        # 4. 在输入框中输入股票代码
        input_elem = page.locator('#searchStockCode')
        input_elem.click()
        time.sleep(0.3)
        
        for char in stock_code:
            input_elem.type(char, delay=80)
        time.sleep(2)
        
        # 5. 从自动补全中选择
        items = page.locator('.ui-autocomplete .ui-menu-item').all()
        print(f'自动补全: {len(items)} 项')
        
        selected = False
        for item in items:
            try:
                text = item.inner_text()
                if stock_code in text:
                    print(f'选择: {text.strip()[:50]}')
                    item.click()
                    selected = True
                    break
            except:
                continue
        
        if not selected and items:
            items[0].click()
            print(f'选择第一项')
        
        time.sleep(1)
        
        # 6. 触发搜索
        # 方式1: 执行JS搜索函数
        # 从config.js中找到搜索函数名
        print('\n触发搜索...')
        
        # 查找搜索按钮
        search_btn = None
        btn_selectors = [
            '#btnSearch',
            'button.btn-search',
            'input[value="Search"]',
            '.search-btn',
            '#searchBtn',
        ]
        for sel in btn_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1000):
                    search_btn = btn
                    print(f'找到搜索按钮: {sel}')
                    break
            except:
                continue
        
        if search_btn:
            search_btn.click()
        else:
            # 使用JS直接触发
            print('尝试JS触发搜索')
            page.evaluate('searchByStock()')  # 从titlesearch.js中发现的函数
            time.sleep(1)
        
        # 等待搜索结果
        time.sleep(8)
        
        # 7. 分析AJAX响应
        print(f'\nAJAX POST响应: {len(ajax_responses)}')
        all_pdfs = []
        all_titles = []
        
        for resp_text in ajax_responses:
            # 从JSF partial-response中提取
            cdatas = re.findall(r'<!\[CDATA\[(.*?)\]\]>', resp_text, re.DOTALL)
            for cd in cdatas:
                # PDF链接
                pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', cd)
                all_pdfs.extend(pdfs)
                
                # 公告标题
                titles = re.findall(r'<a[^>]*class="[^"]*doc[^"]*"[^>]*>([^<]+)</a>', cd)
                all_titles.extend(titles)
                
                # 更宽泛的标题匹配
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', cd, re.DOTALL)
                for row in rows:
                    tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                    if len(tds) >= 2:
                        clean_tds = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]
                        if any(clean.strip() for clean in clean_tds):
                            all_titles.append(' | '.join(clean_tds[:4]))
        
        # 8. 从最终页面内容提取
        content = page.content()
        page_pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', content)
        real_pdfs = [p for p in set(page_pdfs) if '/sehk/' in p or 'listedco' in p]
        
        # 从表格提取
        table_rows = page.locator('table tbody tr, .result-table tr').all()
        print(f'结果表格行: {len(table_rows)}')
        
        announcements = []
        for row in table_rows[:max_results]:
            try:
                cells = row.locator('td').all()
                if len(cells) >= 2:
                    date = cells[0].inner_text().strip() if len(cells) > 0 else ''
                    title = cells[1].inner_text().strip() if len(cells) > 1 else ''
                    link = cells[1].locator('a').first.get_attribute('href') if len(cells) > 1 else ''
                    if title:
                        announcements.append({
                            'date': date,
                            'title': title[:100],
                            'url': link,
                        })
            except:
                continue
        
        # 汇总
        print(f'\n===== 结果 =====')
        print(f'PDF链接: {len(set(all_pdfs + list(real_pdfs)))}')
        print(f'公告: {len(announcements)}')
        print(f'标题: {len(all_titles)}')
        
        for a in announcements[:max_results]:
            print(f'  [{a["date"]}] {a["title"][:60]}')
            if a['url']:
                print(f'    {a["url"][:80]}')
        
        if not announcements and all_pdfs:
            print('\n从AJAX响应中找到PDF:')
            for pdf in set(all_pdfs)[:10]:
                if '/sehk/' in pdf or 'listedco' in pdf:
                    print(f'  {pdf[:80]}')
        
        page.screenshot(path='hkex_final.png')
        browser.close()
        return announcements

# 测试
results = search_hkex('00700')
