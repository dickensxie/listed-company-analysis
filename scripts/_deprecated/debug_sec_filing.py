"""深度调试SEC filing结构"""
import requests
import json
from bs4 import BeautifulSoup
import re

headers = {'User-Agent': 'Mozilla/5.0 (research@investment.com)'}

cik = '0000320193'  # AAPL

# 获取filing列表
resp = requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json', headers=headers, timeout=10)
data = resp.json()
recent = data.get('filings', {}).get('recent', {})

forms = recent.get('form', [])
dates = recent.get('filingDate', [])
accs = recent.get('accessionNumber', [])
primary_docs = recent.get('primaryDocument', [])
primary_doc_descs = recent.get('primaryDocDescription', [])

# 找10-K
for i, form in enumerate(forms[:100]):
    if form == '10-K':
        acc_no = accs[i].replace('-', '')
        primary_doc = primary_docs[i] if i < len(primary_docs) else ''
        primary_desc = primary_doc_descs[i] if i < len(primary_doc_descs) else ''
        
        print(f'10-K: {dates[i]}')
        print(f'Accession: {accs[i]}')
        print(f'Primary Document: {primary_doc}')
        print(f'Primary Doc Description: {primary_desc}')
        
        # 构建完整URL
        base_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}'
        full_url = f'{base_url}/{primary_doc}'
        
        print(f'\n完整URL: {full_url}')
        
        # 下载
        resp2 = requests.get(full_url, headers=headers, timeout=60)
        print(f'状态: {resp2.status_code}, 大小: {len(resp2.text):,} bytes')
        
        if resp2.status_code == 200:
            # 检查是否是HTML
            if '<html' in resp2.text.lower():
                soup = BeautifulSoup(resp2.text, 'html.parser')
                text = soup.get_text()
                
                # 统计治理关键词
                keywords = {
                    'Independent Director': len(re.findall(r'Independent\s+Director', text, re.IGNORECASE)),
                    'Audit Committee': len(re.findall(r'Audit Committee', text, re.IGNORECASE)),
                    'Compensation Committee': len(re.findall(r'Compensation Committee', text, re.IGNORECASE)),
                    'Board of Directors': len(re.findall(r'Board of Directors', text, re.IGNORECASE)),
                    'Corporate Governance': len(re.findall(r'Corporate Governance', text, re.IGNORECASE)),
                }
                
                print(f'\n关键词统计:')
                for k, v in keywords.items():
                    print(f'  {k}: {v}')
                
                # 提取前500字符看结构
                print(f'\n文档开头:')
                print(text[:500])
                
            elif resp2.text.startswith('%PDF'):
                print('这是PDF文件，需要PDF解析')
        
        break
