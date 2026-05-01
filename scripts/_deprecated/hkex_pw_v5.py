"""港交所公告搜索 - 等待结果加载完成"""
from playwright.sync_api import sync_playwright
import time
import re

def search_hkex(stock_code, max_results=10):
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
        
        # 4. 触发搜索 - 使用搜索面板的内置函数
        # 从titlesearch.js中，搜索按钮触发的是ajaxSearch()
        # 先检查JS函数名
        js_functions = page.evaluate('''() => {
            const funcs = [];
            for (let key in window) {
                if (typeof window[key] === 'function' && key.toLowerCase().includes('search')) {
                    funcs.push(key);
                }
            }
            return funcs;
        }''')
        print(f'搜索相关JS函数: {js_functions}')
        
        # 尝试调用搜索函数
        for func_name in ['ajaxSearch', 'doSearch', 'search', 'submitSearch', 'performSearch']:
            try:
                result = page.evaluate(f'() => {{ if (typeof {func_name} === "function") {{ {func_name}(); return "called"; }} return "not found"; }}')
                if result == 'called':
                    print(f'调用 {func_name}() 成功')
                    break
            except:
                pass
        
        # 如果没有JS函数，按Enter
        try:
            input_elem.press('Enter')
            print('按Enter')
        except:
            pass
        
        # 5. 等待结果加载 - 轮询检查表格是否有内容
        print('等待结果加载...')
        for attempt in range(10):
            time.sleep(3)
            
            # 检查结果表格
            rows = page.locator('table tbody tr, .result-table tr').all()
            filled_rows = 0
            for row in rows:
                try:
                    text = row.inner_text().strip()
                    if text and len(text) > 10 and 'Release Time' not in text:
                        filled_rows += 1
                except:
                    continue
            
            print(f'  第{attempt+1}次检查: {filled_rows} 行有内容')
            
            if filled_rows > 0:
                break
            
            # 尝试滚动触发懒加载
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        
        # 6. 提取结果
        content = page.content()
        
        # 方法1: 从表格提取
        announcements = []
        tables = page.locator('table').all()
        
        for table in tables:
            rows = table.locator('tr').all()
            for row in rows:
                try:
                    cells = row.locator('td').all()
                    if len(cells) >= 2:
                        date_text = cells[0].inner_text().strip()
                        link_elem = cells[1].locator('a').first if len(cells) > 1 else None
                        title = ''
                        href = ''
                        
                        if link_elem:
                            try:
                                title = link_elem.inner_text().strip()
                                href = link_elem.get_attribute('href') or ''
                            except:
                                title = cells[1].inner_text().strip()
                        else:
                            title = cells[1].inner_text().strip() if len(cells) > 1 else ''
                        
                        if title and len(title) > 3 and 'Release Time' not in title:
                            announcements.append({
                                'date': date_text,
                                'title': title[:100],
                                'url': href,
                            })
                except:
                    continue
        
        # 方法2: 从HTML正则提取PDF链接
        pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', content)
        real_pdfs = list(set(p for p in pdf_links if '/sehk/' in p or 'listedco' in p))
        
        # 方法3: 从所有a标签提取
        all_links = page.locator('a').all()
        pdf_announcements = []
        for link in all_links:
            try:
                href = link.get_attribute('href') or ''
                text = link.inner_text().strip()
                if '.pdf' in href and text:
                    pdf_announcements.append({
                        'title': text[:100],
                        'url': href,
                    })
            except:
                continue
        
        # 汇总
        print(f'\n===== 搜索结果: {stock_code} =====')
        print(f'表格公告: {len(announcements)}')
        print(f'PDF链接: {len(real_pdfs)}')
        print(f'PDF公告: {len(pdf_announcements)}')
        
        for a in announcements[:max_results]:
            print(f'  [{a["date"]}] {a["title"][:70]}')
        
        for a in pdf_announcements[:max_results]:
            print(f'  {a["title"][:70]}')
            print(f'    → {a["url"][:80]}')
        
        if not announcements and not pdf_announcements:
            # 最终调试：打印所有文本内容
            print('\n页面文本（最后500字符）:')
            body = page.locator('body').inner_text()
            print(body[-500:] if len(body) > 500 else body)
        
        page.screenshot(path='hkex_final_v5.png')
        browser.close()
        return announcements or pdf_announcements

search_hkex('00700')
