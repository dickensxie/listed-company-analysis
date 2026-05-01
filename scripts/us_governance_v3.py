"""SEC 10-K公司治理提取 - 修复版"""
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
            
            print(f'10-K日期: {filing_date}')
            
            # 获取文档列表
            list_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/index.json'
            resp2 = requests.get(list_url, headers=headers, timeout=10)
            
            if resp2.status_code == 200:
                doc_list = resp2.json()
                files = doc_list.get('directory', {}).get('item', [])
                
                # 找最大的htm文件（通常是主文档）
                htm_files = [(f['name'], f.get('size-h', 0)) for f in files if f['name'].endswith(('.htm', '.html'))]
                
                if htm_files:
                    # 按大小排序，取最大的
                    htm_files.sort(key=lambda x: x[1], reverse=True)
                    main_doc = htm_files[0][0]
                    
                    html_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{main_doc}'
                    print(f'下载主文档: {main_doc}')
                    
                    resp3 = requests.get(html_url, headers=headers, timeout=60)
                    if resp3.status_code == 200:
                        print(f'大小: {len(resp3.text):,} bytes')
                        
                        soup = BeautifulSoup(resp3.text, 'html.parser')
                        text = soup.get_text()
                        
                        # 提取治理信息
                        gov = {
                            'ticker': ticker,
                            'filing_date': filing_date,
                            'independent_directors': len(re.findall(r'Independent\s+Director', text, re.IGNORECASE)),
                            'audit_committee': len(re.findall(r'Audit Committee', text, re.IGNORECASE)),
                            'compensation_committee': len(re.findall(r'Compensation Committee', text, re.IGNORECASE)),
                            'nominating_committee': len(re.findall(r'Nominating Committee', text, re.IGNORECASE)),
                            'governance_committee': len(re.findall(r'Governance Committee', text, re.IGNORECASE)),
                            'has_audit_opinion': bool(re.search(r'Report of Independent|Opinion of', text, re.IGNORECASE)),
                            'has_internal_control': bool(re.search(r'Internal Control', text, re.IGNORECASE)),
                        }
                        
                        # 提取董事名单（常见模式）
                        director_pattern = r'(?:Mr\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
                        directors = list(set(re.findall(director_pattern, text[:50000])))  # 只搜前50000字符
                        gov['potential_directors'] = directors[:10]
                        
                        print(f'\n治理信息:')
                        for k, v in gov.items():
                            if k != 'potential_directors':
                                print(f'  {k}: {v}')
                        print(f'  potential_directors: {directors[:5]}')
                        
                        return gov
            
            break
    
    return None

if __name__ == '__main__':
    for ticker in ['AAPL', 'MSFT', 'JPM']:
        result = get_10k_governance(ticker)
        print('\n' + '='*50 + '\n')
