"""港交所公告 - 直接访问股票公告页"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_hkex_announcements(stock_code='00700'):
    """获取港交所公告"""
    
    print(f'=== {stock_code} 公告搜索 ===\n')
    
    # 方案：遍历最近7天的公告目录，查找包含股票代码的公告
    announcements = []
    
    for days_ago in range(7):
        date = datetime.now() - timedelta(days=days_ago)
        date_path = date.strftime('%Y/%m%d')
        
        # 港交所公告目录URL格式
        list_url = f'https://www1.hkexnews.hk/listedco/listconews/sehk/{date_path}/'
        
        try:
            resp = requests.get(list_url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 查找所有公告链接
                for row in soup.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        # 通常格式：股票代码 | 公告标题 | 时间
                        code_cell = cells[0].get_text().strip()
                        title_cell = cells[1]
                        time_cell = cells[2].get_text().strip() if len(cells) > 2 else ''
                        
                        if stock_code in code_cell:
                            link = title_cell.find('a')
                            if link:
                                href = link.get('href', '')
                                title = link.get_text().strip()
                                
                                if 'http' not in href:
                                    href = f'https://www1.hkexnews.hk{href}'
                                
                                announcements.append({
                                    'date': date_path,
                                    'time': time_cell,
                                    'title': title,
                                    'url': href,
                                })
                
                print(f'{date_path}: {resp.status_code}, 找到 {len([a for a in announcements if a["date"] == date_path])} 条')
                
        except Exception as e:
            print(f'{date_path}: 错误 {e}')
    
    print(f'\n总计: {len(announcements)} 条公告\n')
    
    for ann in announcements[:10]:
        print(f"[{ann['date']} {ann['time']}] {ann['title'][:50]}")
        print(f"  {ann['url']}\n")
    
    return announcements

if __name__ == '__main__':
    for code in ['00700', '09988', '01810']:
        get_hkex_announcements(code)
        print('='*60 + '\n')
