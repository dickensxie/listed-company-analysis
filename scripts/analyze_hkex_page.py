"""港交所搜索 - 分析搜索页面HTML结构"""
import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

search_url = 'https://www1.hkexnews.hk/search/titlesearch.xhtml'
resp0 = requests.get(search_url, headers=headers, timeout=15)
print(f'Status: {resp0.status_code}, Size: {len(resp0.text)} bytes')

# 保存HTML
with open('hkex_search_page.html', 'w', encoding='utf-8') as f:
    f.write(resp0.text)
print('Saved to hkex_search_page.html')

# 提取ViewState
vs = re.search(r'name="javax\.faces\.ViewState"\s+value="([^"]*)"', resp0.text)
if vs:
    print(f'ViewState: {vs.group(1)[:60]}...')

# 提取隐藏字段
hiddens = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"', resp0.text)
print(f'Hidden fields: {len(hiddens)}')
for name, val in hiddens:
    print(f'  {name} = {val[:60]}')

# 找form
forms = re.findall(r'<form[^>]*>', resp0.text)
print(f'Forms: {len(forms)}')
for f in forms:
    print(f'  {f}')

# 找所有input
inputs = re.findall(r'<input[^>]*>', resp0.text)
print(f'Inputs: {len(inputs)}')
for inp in inputs:
    print(f'  {inp[:150]}')

# 找按钮
buttons = re.findall(r'<button[^>]*>.*?</button>', resp0.text, re.DOTALL)
print(f'Buttons: {len(buttons)}')
for b in buttons:
    print(f'  {b[:150]}')

# 找select
selects = re.findall(r'<select[^>]*name="([^"]*)"[^>]*>', resp0.text)
print(f'Selects: {selects}')

# 检查是否有iframe
iframes = re.findall(r'<iframe[^>]*src="([^"]*)"', resp0.text)
print(f'Iframes: {iframes}')

# 找JavaScript变量
js_vars = re.findall(r'var\s+(\w+)\s*=\s*([^;]+);', resp0.text)
print(f'JS vars: {len(js_vars)}')
for name, val in js_vars[:10]:
    print(f'  {name} = {val[:80]}')
