"""港交所公告 - 检查页面结构"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

headers = {'User-Agent': 'Mozilla/5.0'}

# 测试访问今天的公告目录
date = datetime.now()
date_path = date.strftime('%Y/%m%d')

url = f'https://www1.hkexnews.hk/listedco/listconews/sehk/{date_path}/'
print(f'URL: {url}\n')

resp = requests.get(url, headers=headers, timeout=10)
print(f'状态: {resp.status_code}')
print(f'大小: {len(resp.text)} bytes\n')

if resp.status_code == 200:
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 打印所有表格
    tables = soup.find_all('table')
    print(f'表格数: {len(tables)}\n')
    
    for i, table in enumerate(tables[:3]):
        print(f'--- 表格 {i} ---')
        rows = table.find_all('tr')[:5]
        for row in rows:
            cells = [cell.get_text().strip()[:30] for cell in row.find_all(['td', 'th'])]
            print(f'  {cells}')
        print()
    
    # 打印所有链接
    links = soup.find_all('a', href=True)[:20]
    print(f'\n链接示例（前20个）:')
    for link in links:
        href = link['href']
        text = link.get_text().strip()[:50]
        if '.pdf' in href:
            print(f'  PDF: {text} -> {href}')
