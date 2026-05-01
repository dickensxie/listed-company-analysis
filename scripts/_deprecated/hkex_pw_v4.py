"""港交所公告搜索 - 正确交互流程"""
from playwright.sync_api import sync_playwright
import time
import re

def search_hkex(stock_code, max_results=10):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 监听所有网络请求中的PDF
        captured_pdfs = []
        def handle_response(response):
            try:
                if '.pdf' in response.url and '/sehk/' in response.url:
                    captured_pdfs.append(response.url)
            except:
                pass
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
        
        # 3. 在搜索输入框输入股票代码
        input_elem = page.locator('#searchStockCode')
        print(f'输入框可见: {input_elem.is_visible()}')
        input_elem.click()
        time.sleep(0.3)
        
        # 逐字符输入
        for char in stock_code:
            input_elem.type(char, delay=100)
        time.sleep(3)  # 等待自动补全
        
        # 4. 检查自动补全下拉
        suggestions = page.locator('.autocomplete-suggestions, .ui-autocomplete').all()
        print(f'自动补全容器: {len(suggestions)}')
        
        # 等待自动补全出现
        try:
            page.wait_for_selector('.autocomplete-suggestion, .ui-menu-item', timeout=5000)
            items = page.locator('.autocomplete-suggestion, .ui-menu-item').all()
            print(f'自动补全选项: {len(items)}')
            
            # 选择匹配的选项
            for item in items:
                try:
                    text = item.inner_text()
                    if stock_code in text:
                        print(f'选择: {text.strip()[:60]}')
                        item.click()
                        break
                except:
                    continue
            else:
                if items:
                    items[0].click()
                    print(f'选择第一项')
        except:
            print('自动补全超时，尝试直接输入')
        
        time.sleep(2)
        
        # 5. 检查stockId隐藏字段是否已设置
        stock_id_val = page.locator('input[name="stockId"]').first.get_attribute('value') or ''
        print(f'stockId: {stock_id_val}')
        
        # 6. 设置日期范围
        try:
            from_input = page.locator('#searchDate-From')
            to_input = page.locator('#searchDate-To')
            if from_input.is_visible():
                from_input.fill('2024/01/01')
            if to_input.is_visible():
                to_input.fill('2026/12/31')
        except:
            pass
        
        # 7. 点击搜索按钮
        # 从搜索面板HTML可知，搜索按钮可能是submit或自定义按钮
        # 尝试查找
        search_clicked = False
        
        # 方式1: 查找搜索按钮
        for sel in ['.btn-search', '#btnSearch', 'button:has-text("Search")', '.search-button']:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    print(f'点击搜索: {sel}')
                    search_clicked = True
                    break
            except:
                continue
        
        # 方式2: 在输入框按Enter
        if not search_clicked:
            input_elem.press('Enter')
            print('按Enter搜索')
        
        # 8. 等待结果
        time.sleep(10)
        
        # 9. 提取结果
        content = page.content()
        
        # 从表格提取公告
        announcements = []
        
        # 查找结果表格
        tables = page.locator('table').all()
        print(f'\n表格数: {len(tables)}')
        
        for table in tables:
            rows = table.locator('tr').all()
            for row in rows:
                try:
                    cells = row.locator('td').all()
                    if len(cells) >= 2:
                        # 第一个td通常是日期，第二个是标题/链接
                        date_text = cells[0].inner_text().strip()
                        link_elem = cells[1].locator('a').first
                        title = link_elem.inner_text().strip() if link_elem else cells[1].inner_text().strip()
                        href = link_elem.get_attribute('href') if link_elem else ''
                        
                        if title and len(title) > 3:
                            announcements.append({
                                'date': date_text,
                                'title': title[:100],
                                'url': href,
                            })
                except:
                    continue
        
        # 也从PDF链接提取
        pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', content)
        real_pdfs = list(set(p for p in pdf_links if '/sehk/' in p or 'listedco' in p))
        
        # 汇总
        print(f'\n===== 搜索结果: {stock_code} =====')
        print(f'公告数: {len(announcements)}')
        print(f'公告PDF: {len(real_pdfs)}')
        print(f'网络捕获PDF: {len(captured_pdfs)}')
        
        for a in announcements[:max_results]:
            print(f'  [{a["date"]}] {a["title"][:70]}')
            if a['url']:
                print(f'    → {a["url"][:80]}')
        
        if not announcements:
            # 打印部分内容调试
            print(f'\n页面内容（搜索结果区域）:')
            result_area = page.locator('#searchResult, .result-table, .search-results, .result-container').all()
            if result_area:
                for area in result_area:
                    try:
                        print(area.inner_text()[:500])
                    except:
                        pass
            else:
                # 打印所有表格文本
                for table in tables:
                    try:
                        txt = table.inner_text()[:500]
                        if txt.strip():
                            print(f'Table: {txt}')
                    except:
                        pass
        
        page.screenshot(path='hkex_final_v4.png')
        browser.close()
        return announcements

# 测试
search_hkex('00700')
