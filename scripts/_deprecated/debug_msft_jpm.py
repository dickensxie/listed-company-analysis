"""修复MSFT/JPM的CIK"""
import requests

headers = {'User-Agent': 'Mozilla/5.0 (research@investment.com)'}

# 测试MSFT和JPM的filing列表
test_ciks = {
    'MSFT': '0000789019',
    'JPM': '0000019617',
}

for ticker, cik in test_ciks.items():
    print(f'=== {ticker} (CIK: {cik}) ===')
    
    url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    resp = requests.get(url, headers=headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        recent = data.get('filings', {}).get('recent', {})
        
        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        
        # 找10-K
        print(f'最近filing类型: {forms[:30]}')
        
        for i, form in enumerate(forms[:100]):
            if form == '10-K':
                print(f'找到10-K: {dates[i]}')
                break
        else:
            print('前100个filing中未找到10-K')
    else:
        print(f'错误: {resp.status_code}')
    
    print()
