"""Inspect report.py around line 900"""
f = open(r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py', 'rb')
lines = f.readlines()
f.close()

for i in range(892, 925):
    raw = lines[i]
    for enc in ['utf-8', 'gbk', 'latin-1']:
        try:
            txt = raw.decode(enc, errors='replace')
            print(f'L{i+1} [{enc}]: {txt.rstrip()[:120]}')
            break
        except:
            pass
    print()
