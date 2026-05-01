"""SEC 10-K公司治理提取 - 最终版"""
import requests
import re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (research@investment.com)'}

def get_10k_governance(ticker='AAPL'):
    """从SEC 10-K提取公司治理信息"""
    
    cik_map = {
        'AAPL': '0000320193',
        'MSFT': '0000789019',
        'GOOGL': '0001652044',
        'JPM': '0000019617',
        'AMZN': '0001018724',
    }
    
    cik = cik_map.get(ticker.upper())
    if not cik:
        return None
    
    print(f'=== {ticker} ===')
    
    # 获取filing列表
    resp = requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json', headers=headers, timeout=10)
    if resp.status_code != 200:
        return None
    
    data = resp.json()
    recent = data.get('filings', {}).get('recent', {})
    
    forms = recent.get('form', [])
    dates = recent.get('filingDate', [])
    accs = recent.get('accessionNumber', [])
    
    # 找10-K
    for i, form in enumerate(forms[:100]):
        if form == '10-K':
            acc_no = accs[i].replace('-', '')
            filing_date = dates[i]
            
            print(f'10-K日期: {filing_date}, Accession: {accs[i]}')
            
            # 获取filing文档
            filing_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{accs[i]}-index.htm'
            print(f'访问filing索引页...')
            
            resp2 = requests.get(filing_url, headers=headers, timeout=30)
            if resp2.status_code == 200:
                soup = BeautifulSoup(resp2.text, 'html.parser')
                
                # 找主10-K文档（通常是第一个htm/html链接，且名称包含10-k或为accession号）
                main_doc_url = None
                for table in soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            link = cells[0].find('a')
                            if link:
                                href = link.get('href', '')
                                text = link.get_text().lower()
                                desc = cells[1].get_text().lower() if len(cells) > 1 else ''
                                
                                # 主10-K文档特征
                                if href.endswith(('.htm', '.html')):
                                    if '10-k' in text or 'complete submission' in desc or accs[i].lower() in text:
                                        main_doc_url = f'https://www.sec.gov{href}' if href.startswith('/') else href
                                        print(f'找到主文档: {text} - {desc}')
                                        break
                    if main_doc_url:
                        break
                
                # 如果没找到，取第一个htm文件
                if not main_doc_url:
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.endswith(('.htm', '.html')) and 'index' not in href.lower():
                            main_doc_url = f'https://www.sec.gov{href}' if href.startswith('/') else href
                            print(f'使用第一个htm文档: {href}')
                            break
                
                if main_doc_url:
                    print(f'下载: {main_doc_url}')
                    resp3 = requests.get(main_doc_url, headers=headers, timeout=60)
                    
                    if resp3.status_code == 200:
                        print(f'文档大小: {len(resp3.text):,} bytes\n')
                        
                        soup3 = BeautifulSoup(resp3.text, 'html.parser')
                        text = soup3.get_text()
                        
                        # 提取治理信息
                        gov = {
                            'ticker': ticker,
                            'filing_date': filing_date,
                            'doc_size': len(resp3.text),
                            'independent_directors': len(re.findall(r'Independent\s+Director', text, re.IGNORECASE)),
                            'audit_committee': len(re.findall(r'Audit Committee', text, re.IGNORECASE)),
                            'compensation_committee': len(re.findall(r'Compensation Committee', text, re.IGNORECASE)),
                            'nominating_committee': len(re.findall(r'Nominat\w* Committee', text, re.IGNORECASE)),
                            'governance_committee': len(re.findall(r'Governance Committee', text, re.IGNORECASE)),
                            'has_audit_opinion': bool(re.search(r'Report of Independent|Opinion of', text, re.IGNORECASE)),
                            'has_internal_control': bool(re.search(r'Internal Control', text, re.IGNORECASE)),
                        }
                        
                        # 提取董事姓名
                        director_pattern = r'(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)'
                        directors = list(set(re.findall(director_pattern, text[:100000])))[:15]
                        gov['directors'] = directors
                        
                        print('治理信息:')
                        for k, v in gov.items():
                            if k != 'directors':
                                print(f'  {k}: {v}')
                        if directors:
                            print(f'  directors: {directors[:8]}')
                        
                        return gov
            
            break
    
    print('未找到10-K')
    return None

if __name__ == '__main__':
    for ticker in ['AAPL', 'MSFT', 'JPM']:
        result = get_10k_governance(ticker)
        print('\n' + '='*60 + '\n')
