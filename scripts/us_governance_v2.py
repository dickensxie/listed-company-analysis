"""修复版：SEC 10-K公司治理信息提取"""
import requests
import re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (research@investment.com)'}

def extract_governance_from_10k(ticker='AAPL'):
    """从SEC 10-K提取公司治理信息"""
    
    # CIK映射
    cik_map = {
        'AAPL': '0000320193',
        'MSFT': '0000789019',
        'GOOGL': '0001652044',
        'AMZN': '0001018724',
        'META': '0001326801',
        'NVDA': '0001045810',
        'TSLA': '0001318605',
        'JPM': '0000019617',
        'V': '0001403161',
        'WMT': '0000104169',
    }
    
    cik = cik_map.get(ticker.upper())
    if not cik:
        print(f'未找到 {ticker} 的CIK')
        return None
    
    print(f'=== {ticker} (CIK: {cik}) ===')
    
    # 获取filing列表
    filing_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    resp = requests.get(filing_url, headers=headers, timeout=10)
    
    if resp.status_code != 200:
        print(f'获取filing列表失败: {resp.status_code}')
        return None
    
    data = resp.json()
    recent = data.get('filings', {}).get('recent', {})
    
    forms = recent.get('form', [])
    dates = recent.get('filingDate', [])
    accs = recent.get('accessionNumber', [])
    
    # 找最近的10-K（可能在前100个）
    print(f'搜索最近100个filing中的10-K...')
    for i, form in enumerate(forms[:100]):
        if form == '10-K':
            acc_no = accs[i].replace('-', '')
            filing_date = dates[i]
            
            print(f'找到10-K: {filing_date}')
            
            # 构建文档列表URL
            list_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/index.json'
            
            # 获取文档列表
            resp2 = requests.get(list_url, headers=headers, timeout=10)
            if resp2.status_code == 200:
                try:
                    doc_list = resp2.json()
                    files = doc_list.get('directory', {}).get('item', [])
                    
                    # 找主文档（通常是完整10-K）
                    main_doc = None
                    for f in files:
                        name = f.get('name', '')
                        if name.endswith('.htm') or name.endswith('.html'):
                            if '10-k' in name.lower() or name == f'{accs[i]}.htm':
                                main_doc = name
                                break
                    
                    if not main_doc:
                        # 取第一个htm文件
                        for f in files:
                            name = f.get('name', '')
                            if name.endswith('.htm') or name.endswith('.html'):
                                main_doc = name
                                break
                    
                    if main_doc:
                        html_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{main_doc}'
                        print(f'下载: {html_url}')
                        
                        resp3 = requests.get(html_url, headers=headers, timeout=30)
                        if resp3.status_code == 200:
                            print(f'10-K大小: {len(resp3.text)} bytes')
                            
                            # 提取治理信息
                            soup = BeautifulSoup(resp3.text, 'html.parser')
                            text = soup.get_text()
                            
                            governance = {
                                'ticker': ticker,
                                'filing_date': filing_date,
                                'source': 'SEC 10-K',
                            }
                            
                            # 独立董事
                            governance['independent_director_mentions'] = len(re.findall(r'Independent\s+Director', text, re.IGNORECASE))
                            
                            # 委员会
                            committees = {}
                            for comm in ['Audit', 'Compensation', 'Nominating', 'Governance']:
                                count = len(re.findall(f'{comm} Committee', text, re.IGNORECASE))
                                if count > 0:
                                    committees[comm] = count
                            governance['committees'] = committees
                            
                            # 审计意见
                            governance['has_audit_opinion'] = bool(re.search(r'Report of Independent Registered|Opinion of the Independent', text, re.IGNORECASE))
                            
                            # 内控报告
                            governance['has_internal_control'] = bool(re.search(r'Internal Control over Financial Reporting', text, re.IGNORECASE))
                            
                            print(f'\n提取结果:')
                            for k, v in governance.items():
                                print(f'  {k}: {v}')
                            
                            return governance
                except Exception as e:
                    print(f'解析文档列表失败: {e}')
            
            break
    
    print('未找到10-K或下载失败')
    return None

if __name__ == '__main__':
    for ticker in ['AAPL', 'MSFT']:
        result = extract_governance_from_10k(ticker)
        print('\n' + '='*50 + '\n')
