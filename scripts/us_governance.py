"""SEC 10-K公司治理提取模块"""
import requests
import re
from bs4 import BeautifulSoup
import json

headers = {'User-Agent': 'Mozilla/5.0 (research@investment.com)'}

# CIK映射（常见美股）
CIK_MAP = {
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
    'BABA': '0001614520',
    'JD': '0001515971',
    'PDD': '0001737806',
}

def extract_us_governance(ticker):
    """从SEC 10-K提取美股公司治理信息
    
    Args:
        ticker: 股票代码（如AAPL）
    
    Returns:
        dict: 治理信息
    """
    
    cik = CIK_MAP.get(ticker.upper())
    if not cik:
        return {'error': f'未找到 {ticker} 的CIK，请添加到CIK_MAP'}
    
    try:
        # 1. 获取filing列表
        resp = requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json', headers=headers, timeout=10)
        if resp.status_code != 200:
            return {'error': f'SEC API错误: {resp.status_code}'}
        
        data = resp.json()
        recent = data.get('filings', {}).get('recent', {})
        
        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        accs = recent.get('accessionNumber', [])
        primary_docs = recent.get('primaryDocument', [])
        
        # 2. 找最近的10-K（扩大搜索范围到全部filing）
        for i, form in enumerate(forms):
            if form == '10-K':
                acc_no = accs[i].replace('-', '')
                primary_doc = primary_docs[i] if i < len(primary_docs) else ''
                filing_date = dates[i]
                
                if not primary_doc:
                    continue
                
                # 3. 下载10-K
                doc_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{primary_doc}'
                resp2 = requests.get(doc_url, headers=headers, timeout=60)
                
                if resp2.status_code != 200:
                    continue
                
                # 4. 提取治理信息
                soup = BeautifulSoup(resp2.text, 'html.parser')
                text = soup.get_text()
                
                governance = {
                    'ticker': ticker,
                    'cik': cik,
                    'filing_date': filing_date,
                    'source': 'SEC 10-K',
                    'doc_size': len(resp2.text),
                    
                    # 委员会
                    'audit_committee': len(re.findall(r'Audit Committee', text, re.IGNORECASE)),
                    'compensation_committee': len(re.findall(r'Compensation Committee', text, re.IGNORECASE)),
                    'nominating_committee': len(re.findall(r'Nominat\w* Committee', text, re.IGNORECASE)),
                    'governance_committee': len(re.findall(r'Governance Committee', text, re.IGNORECASE)),
                    
                    # 董事会
                    'board_mentions': len(re.findall(r'Board of Directors', text, re.IGNORECASE)),
                    'independent_director_mentions': len(re.findall(r'Independent\s+Director', text, re.IGNORECASE)),
                    
                    # 审计
                    'has_audit_opinion': bool(re.search(r'Report of Independent|Opinion of', text, re.IGNORECASE)),
                    'has_internal_control': bool(re.search(r'Internal Control', text, re.IGNORECASE)),
                    
                    # 公司治理章节
                    'governance_section': len(re.findall(r'Corporate Governance', text, re.IGNORECASE)),
                }
                
                # 5. 提取董事姓名（启发式）
                director_pattern = r'(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)'
                directors = list(set(re.findall(director_pattern, text[:100000])))[:20]
                governance['directors'] = directors
                
                # 6. 计算治理评分（简化版）
                score = 0
                if governance['audit_committee'] > 0: score += 15
                if governance['compensation_committee'] > 0: score += 15
                if governance['nominating_committee'] > 0: score += 10
                if governance['governance_committee'] > 0: score += 10
                if governance['independent_director_mentions'] > 3: score += 20
                if governance['has_audit_opinion']: score += 15
                if governance['has_internal_control']: score += 15
                governance['governance_score'] = min(score, 100)
                
                return governance
        
        return {'error': '未找到10-K'}
        
    except Exception as e:
        return {'error': str(e)}


if __name__ == '__main__':
    # 测试
    for ticker in ['AAPL', 'MSFT', 'JPM']:
        result = extract_us_governance(ticker)
        print(f'\n=== {ticker} ===')
        for k, v in result.items():
            if k != 'directors':
                print(f'{k}: {v}')
        if result.get('directors'):
            print(f'directors: {result["directors"][:8]}')
