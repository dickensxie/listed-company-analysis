"""测试SEC EDGAR获取10-K HTML并提取公司治理信息"""
import requests
import re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (research@investment.com)'}

# AAPL CIK
aapl_cik = '0000320193'

# 1. 获取filing列表
print('=== 获取AAPL 10-K filing列表 ===')
filing_url = f'https://data.sec.gov/submissions/CIK{aapl_cik}.json'
resp = requests.get(filing_url, headers=headers, timeout=10)

if resp.status_code == 200:
    data = resp.json()
    filings = data.get('filings', {}).get('recent', {})
    forms = filings.get('form', [])
    dates = filings.get('filingDate', [])
    accs = filings.get('accessionNumber', [])
    docs = filings.get('primaryDocument', [])
    
    # 找最近的10-K
    for i, form in enumerate(forms[:30]):
        if form == '10-K':
            acc_no = accs[i].replace('-', '')
            primary_doc = docs[i]
            print(f'最近10-K: {dates[i]}')
            print(f'Accession: {accs[i]}')
            print(f'Primary doc: {primary_doc}')
            
            # 构建HTML URL
            base_url = f'https://www.sec.gov/Archives/edgar/data/{aapl_cik}/{acc_no}'
            html_url = f'{base_url}/{primary_doc}'
            print(f'10-K URL: {html_url}')
            
            # 下载10-K HTML
            resp2 = requests.get(html_url, headers=headers, timeout=30)
            print(f'\n下载状态: {resp2.status_code}, 大小: {len(resp2.text)} bytes')
            
            if resp2.status_code == 200:
                # 提取公司治理相关章节
                soup = BeautifulSoup(resp2.text, 'html.parser')
                text = soup.get_text()
                
                # 查找治理关键词
                gov_keywords = [
                    'Board of Directors',
                    'Corporate Governance',
                    'Audit Committee',
                    'Compensation Committee',
                    'Nominating Committee',
                    'Independent Director',
                    'Executive Officer',
                    'Director Independence',
                ]
                
                print('\n=== 公司治理关键词出现次数 ===')
                for kw in gov_keywords:
                    count = len(re.findall(kw, text, re.IGNORECASE))
                    if count > 0:
                        print(f'{kw}: {count}次')
                
                # 提取董事信息（常见模式）
                director_pattern = r'(?:Director|Board Member)[^\n]{0,200}'
                directors = re.findall(director_pattern, text, re.IGNORECASE)
                print(f'\n董事相关片段: {len(directors)}个')
                if len(directors) > 0:
                    print(f'示例: {directors[0][:100]}...')
            
            break
else:
    print(f'获取filing列表失败: {resp.status_code}')
