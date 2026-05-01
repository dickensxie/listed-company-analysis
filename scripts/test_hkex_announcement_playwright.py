"""港交所Playwright公告搜索测试"""
import asyncio
from playwright.async_api import async_playwright
import re

async def search_hkex_announcements(stock_code='00700'):
    """搜索港交所公告并尝试获取全文"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        results = []
        
        try:
            # 访问港交所披露易首页
            print(f'访问港交所披露易首页...')
            await page.goto('https://www.hkexnews.hk/', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # 尝试搜索框
            print(f'查找搜索框...')
            search_input = await page.query_selector('input[placeholder*="Stock"], input[name*="stock"], input[type="text"]')
            
            if search_input:
                print(f'找到搜索框，输入股票代码: {stock_code}')
                await search_input.fill(stock_code)
                await page.wait_for_timeout(1000)
                
                # 按Enter或点击搜索按钮
                await search_input.press('Enter')
                await page.wait_for_timeout(5000)
                
                # 检查结果
                content = await page.content()
                print(f'搜索后页面长度: {len(content)} bytes')
                
                # 提取PDF链接
                pdf_links = re.findall(r'href="([^"]*\.pdf)"', content)
                print(f'找到PDF链接: {len(pdf_links)}个')
                
                for link in pdf_links[:5]:
                    if 'http' not in link:
                        link = f'https://www1.hkexnews.hk{link}'
                    print(f'  - {link}')
                    results.append(link)
            else:
                print('未找到搜索框')
                
                # 尝试直接访问股票公告页
                direct_url = f'https://www.hkexnews.hk/listedco/listconews/sehk/{stock_code}/'
                print(f'尝试直接访问: {direct_url}')
                await page.goto(direct_url, timeout=30000)
                await page.wait_for_timeout(3000)
                
                content = await page.content()
                pdf_links = re.findall(r'href="([^"]*\.pdf)"', content)
                print(f'直接页面PDF链接: {len(pdf_links)}个')
                
        except Exception as e:
            print(f'错误: {e}')
        finally:
            await browser.close()
        
        return results

if __name__ == '__main__':
    results = asyncio.run(search_hkex_announcements('00700'))
    print(f'\n结果: {len(results)}个公告')
