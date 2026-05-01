import re, os

skill = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts'
apis = {}
for fn in os.listdir(skill):
    if fn.endswith('.py') and fn not in ['__init__.py'] and '__pycache__' not in fn:
        path = os.path.join(skill, fn)
        with open(path, encoding='utf-8') as f:
            txt = f.read()
        urls = re.findall(r'https?://[^\s\'"\\]+', txt)
        if urls:
            apis[fn] = sorted(set(urls))

for fn, urls in sorted(apis.items()):
    print(f'=== {fn} ===')
    for u in urls:
        print(f'  {u}')
    print()
