"""港交所公告搜索 - 使用已知API"""
import requests
import re
from bs4 import BeautifulSoup
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_hkex_announcements(stock_code='00700', days=30):
    """获取港交所公告列表
    
    方法：使用港交所prefix API获取stockId，然后构造公告URL
    """
    
    print(f'=== 港交所公告搜索: {stock_code} ===\n')
    
    # 1. 获取stockId
    prefix_url = f'https://www.hkexnews.hk/search/prefix.do?callback=callback&lang=EN&type=A&name={stock_code}&market=SEHK'
    
    resp = requests.get(prefix_url, headers=headers, timeout=10)
    print(f'prefix API状态: {resp.status_code}')
    
    if resp.status_code == 200:
        # 解析JSONP
        match = re.search(r'callback\((.*)\)', resp.text)
        if match:
            data = json.loads(match.group(1))
            stock_info = data.get('stockInfo', [])
            
            if stock_info:
                stock_id = stock_info[0].get('stockId')
                stock_name = stock_info[0].get('name')
                print(f'股票: {stock_name} ({stock_code}), stockId: {stock_id}\n')
            else:
                print('未找到股票信息')
                return []
    
    # 2. 尝试直接访问公告页（按日期）
    # 格式: https://www1.hkexnews.hk/listedco/listconews/sehk/YYYY/MMDD/
    from datetime import datetime, timedelta
    
    announcements = []
    
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y/%m%d')
        
        list_url = f'https://www1.hkexnews.hk/listedco/listconews/sehk/{date_str}/'
        
        try:
            resp2 = requests.get(list_url, headers=headers, timeout=5)
            if resp2.status_code == 200:
                # 提取PDF链接
                soup = BeautifulSoup(resp2.text, 'html.parser')
                
                # 查找包含股票代码的公告
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text()
                    
                    if '.pdf' in href and stock_code in text:
                        if 'http' not in href:
                            href = f'https://www1.hkexnews.hk{href}'
                        
                        announcements.append({
                            'date': date_str,
                            'title': text[:100],
                            'url': href,
                        })
                        
        except:
            pass
        
        if len(announcements) >= 10:
            break
    
    print(f'找到公告: {len(announcements)}条\n')
    for ann in announcements[:10]:
        print(f"[{ann['date']}] {ann['title'][:60]}")
        print(f"  {ann['url']}\n")
    
    return announcements

if __name__ == '__main__':
    for code in ['00700', '09988', '01810']:
        result = get_hkex_announcements(code, days=7)
        print('='*60 + '\n')
