"""调试SEC EDGAR API"""
import requests
import json

headers = {'User-Agent': 'Mozilla/5.0 (research@investment.com)'}

# 测试AAPL
cik = '0000320193'
url = f'https://data.sec.gov/submissions/CIK{cik}.json'

print(f'请求: {url}\n')
resp = requests.get(url, headers=headers, timeout=10)
print(f'状态: {resp.status_code}')

if resp.status_code == 200:
    data = resp.json()
    
    # 打印顶层键
    print(f'顶层键: {list(data.keys())}\n')
    
    # 检查filings结构
    if 'filings' in data:
        print('filings键存在')
        recent = data['filings'].get('recent', {})
        print(f'recent键: {list(recent.keys())[:10]}')
        
        if 'form' in recent:
            forms = recent['form'][:20]
            print(f'\n最近20个filing类型: {forms}')
            
            # 找10-K
            for i, f in enumerate(forms):
                if f == '10-K':
                    print(f'\n找到10-K在索引 {i}')
                    print(f'  filingDate: {recent["filingDate"][i]}')
                    print(f'  accessionNumber: {recent["accessionNumber"][i]}')
                    print(f'  primaryDocument: {recent.get("primaryDocument", ["N/A"]*20)[i]}')
                    break
    else:
        # 可能直接是filing数据
        print('检查其他结构...')
        if 'filings' not in data:
            # 打印前100字符
            print(f'数据预览: {str(data)[:500]}')
