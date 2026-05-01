"""测试北交所官网公告爬取"""
import requests
from bs4 import BeautifulSoup
import re
import json

# 北交所公告页面
url = 'https://www.bse.cn/disclosure/notice.html'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

resp = requests.get(url, headers=headers, timeout=10)
print(f'状态码: {resp.status_code}')
print(f'内容长度: {len(resp.text)} bytes')

# 检查是否为SPA
soup = BeautifulSoup(resp.text, 'html.parser')
scripts = soup.find_all('script')
print(f'Script标签数: {len(scripts)}')

# 查找API端点
api_patterns = re.findall(r'(https?://[^\s"\']+(?:api|list|notice|disclosure)[^\s"\']*)', resp.text)
print(f'发现API候选: {len(set(api_patterns))}个')
for api in list(set(api_patterns))[:5]:
    print(f'  - {api}')

# 查找data-*属性或Vue相关
vue_hints = re.findall(r'(Vue|__vue__|data-v-|v-if|v-for)', resp.text)
print(f'Vue线索: {len(vue_hints)}个')

# 尝试北交所公告API（常见模式）
test_apis = [
    'https://www.bse.cn/api/disclosure/notice',
    'https://www.bse.cn/disclosure/notice/list',
    'https://www.bse.cn/api/notice/list',
]

for api in test_apis:
    try:
        r = requests.get(api, headers=headers, timeout=5)
        print(f'\n测试 {api}')
        print(f'  状态: {r.status_code}, 长度: {len(r.text)}')
        if r.status_code == 200 and len(r.text) > 100:
            # 尝试解析JSON
            try:
                data = r.json()
                print(f'  JSON键: {list(data.keys())[:5]}')
            except:
                print(f'  非JSON响应')
    except Exception as e:
        print(f'  错误: {e}')
