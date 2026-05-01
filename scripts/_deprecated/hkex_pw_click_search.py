"""港交所搜索 - 点击SEARCH按钮提取结果"""
from playwright.sync_api import sync_playwright
import time
import re
import json

def search_hkex(stock_code='00700', max_pdfs=20):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. 加载搜索页
        page.goto('https://www1.hkexnews.hk/search/titlesearch.xhtml', timeout=30000)
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # 2. 接受Cookie
        try:
            page.locator('button:has-text("Accept"), a:has-text("Accept")').first.click(timeout=3000)
            time.sleep(0.5)
        except:
            pass
        
        # 3. 输入股票代码并选择
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
                text = item.inner_text().strip()
                if stock_code in text:
                    item.click()
                    print(f'已选择: {text.strip()[:50]}')
                    break
        except:
            print('自动补全超时')
        
        time.sleep(1)
        
        # 4. 点击SEARCH按钮
        print('\n=== 点击SEARCH按钮 ===')
        search_btn = page.locator('.filter__btn-applyFilters-js')
        try:
            search_btn.click(timeout=5000)
            print('SEARCH按钮已点击')
        except:
            print('SEARCH按钮点击失败，尝试Enter')
            page.keyboard.press('Enter')
        
        # 等待结果加载
        time.sleep(5)
        
        # 5. 提取搜索结果
        print('\n=== 提取搜索结果 ===')
        
        # 方法1：从表格提取
        results = page.evaluate('''() => {
            const rows = document.querySelectorAll('.title-search-result table tbody tr, .table tbody tr');
            const data = [];
            for (const row of rows) {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 3) {
                    const releaseTime = cells[0]?.textContent?.trim()?.substring(0, 30) || '';
                    const stockCode = cells[1]?.textContent?.trim()?.substring(0, 10) || '';
                    const stockName = cells[2]?.textContent?.trim()?.substring(0, 30) || '';
                    const docLink = cells[3]?.querySelector('a');
                    const docTitle = docLink?.textContent?.trim()?.substring(0, 80) || '';
                    const docHref = docLink?.href || '';
                    const headline = cells[4]?.textContent?.trim()?.substring(0, 100) || '';
                    data.push({releaseTime, stockCode, stockName, docTitle, docHref, headline});
                }
            }
            return data;
        }''')
        
        print(f'表格行数: {len(results)}')
        for i, r in enumerate(results[:10]):
            print(f'\n--- 结果 {i+1} ---')
            print(f"  时间: {r['releaseTime']}")
            print(f"  代码: {r['stockCode']} 名称: {r['stockName']}")
            print(f"  标题: {r['docTitle']}")
            print(f"  链接: {r['docHref'][:100]}")
            if r['headline']:
                print(f"  摘要: {r['headline'][:80]}")
        
        # 方法2：直接提取所有PDF链接
        print('\n=== PDF链接 ===')
        pdf_data = page.evaluate('''() => {
            const links = document.querySelectorAll('a[href*=".pdf"]');
            return Array.from(links).slice(0, 30).map(a => ({
                href: a.href?.substring(0, 150),
                text: a.textContent?.trim()?.substring(0, 60),
            }));
        }''')
        
        print(f'PDF链接数: {len(pdf_data)}')
        for pdf in pdf_data:
            # 过滤帮助文档
            href = pdf['href']
            if '/sehk/' in href or '/gem/' in href:
                print(f"  ✅ {pdf['text'][:40]} → {href[-80:]}")
            else:
                print(f"  ⚠️ {pdf['text'][:40]} → {href[-80:]}")
        
        # 6. 检查是否需要加载更多
        print('\n=== 检查Load More ===')
        load_more = page.evaluate('''() => {
            const btn = document.querySelector('.load-more-btn, [class*="loadMore"], [class*="load-more"]');
            if (btn) return {text: btn.textContent?.trim()?.substring(0, 30), visible: btn.offsetParent !== null};
            return null;
        }''')
        if load_more:
            print(f'Load More按钮: {load_more}')
        else:
            print('无Load More按钮')
        
        # 7. 获取总结果数
        total_info = page.evaluate('''() => {
            const total = document.querySelector('.total-count, .result-count, [class*="totalCount"], [class*="resultCount"]');
            if (total) return total.textContent?.trim();
            // 尝试从表格信息提取
            const info = document.querySelector('.search-result-info, .result-info');
            if (info) return info.textContent?.trim()?.substring(0, 100);
            return null;
        }''')
        if total_info:
            print(f'结果总数信息: {total_info}')
        
        browser.close()
        return results

if __name__ == '__main__':
    results = search_hkex('00700')
    print(f'\n共提取 {len(results)} 条公告')
