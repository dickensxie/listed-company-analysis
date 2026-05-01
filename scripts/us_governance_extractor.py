"""SEC 10-K公司治理信息提取"""
import requests
import re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (research@investment.com)'}

def extract_governance_from_10k(ticker='AAPL'):
    """从SEC 10-K提取公司治理信息"""
    
    # CIK映射（常见股票）
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
    
    print(f'=== {ticker} (CIK: {cik}) 公司治理提取 ===\n')
    
    # 获取filing列表
    filing_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    resp = requests.get(filing_url, headers=headers, timeout=10)
    
    if resp.status_code != 200:
        print(f'获取filing列表失败: {resp.status_code}')
        return None
    
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
            filing_date = dates[i]
            
            print(f'最近10-K日期: {filing_date}')
            
            # 下载10-K
            base_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}'
            html_url = f'{base_url}/{primary_doc}'
            
            print(f'下载10-K...')
            resp2 = requests.get(html_url, headers=headers, timeout=30)
            
            if resp2.status_code != 200:
                print(f'下载失败: {resp2.status_code}')
                return None
            
            print(f'10-K大小: {len(resp2.text)} bytes\n')
            
            # 解析HTML
            soup = BeautifulSoup(resp2.text, 'html.parser')
            text = soup.get_text()
            
            # 提取治理信息
            governance = {
                'ticker': ticker,
                'filing_date': filing_date,
                'source': 'SEC 10-K',
            }
            
            # 1. 董事会信息
            board_match = re.search(r'(?:Board of Directors|Directors)[^\n]{0,500}', text, re.IGNORECASE)
            if board_match:
                governance['board_section'] = board_match.group(0)[:300]
            
            # 2. 独立董事
            ind_dir_count = len(re.findall(r'Independent\s+Director', text, re.IGNORECASE))
            governance['independent_director_mentions'] = ind_dir_count
            
            # 3. 委员会
            committees = {}
            for comm in ['Audit', 'Compensation', 'Nominating', 'Governance']:
                pattern = f'{comm} Committee'
                count = len(re.findall(pattern, text, re.IGNORECASE))
                if count > 0:
                    committees[comm.lower()] = count
            governance['committees'] = committees
            
            # 4. 高管薪酬（查找表格或章节）
            comp_match = re.search(r'(?:Executive Compensation|Compensation Discussion)[^\n]{0,200}', text, re.IGNORECASE)
            if comp_match:
                governance['compensation_section'] = comp_match.group(0)
            
            # 5. 审计意见
            audit_match = re.search(r'(?:Report of Independent Registered|Opinion of the Independent)[^\n]{0,200}', text, re.IGNORECASE)
            if audit_match:
                governance['audit_opinion'] = audit_match.group(0)
            
            # 6. 内控报告
            ic_match = re.search(r'(?:Internal Control over Financial Reporting)[^\n]{0,200}', text, re.IGNORECASE)
            if ic_match:
                governance['internal_control'] = ic_match.group(0)
            
            # 打印结果
            print('提取结果:')
            for k, v in governance.items():
                if k != 'board_section':
                    print(f'  {k}: {v}')
            
            return governance
    
    print('未找到10-K')
    return None

if __name__ == '__main__':
    # 测试多只股票
    for ticker in ['AAPL', 'MSFT', 'JPM']:
        result = extract_governance_from_10k(ticker)
        print('\n' + '='*60 + '\n')
