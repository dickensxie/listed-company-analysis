"""Find actual content of report.py in all encodings"""
import os

rp = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'

# Try GBK first
try:
    with open(rp, 'r', encoding='gbk') as f:
        content_gbk = f.read()
    print(f"GBK: OK, size={len(content_gbk)}")
    has_strategy = '_section_strategy' in content_gbk
    has_generate = '_generate_timeline' in content_gbk
    print(f"  has _section_strategy: {has_strategy}")
    print(f"  has _generate_timeline: {has_generate}")
    if has_strategy:
        idx = content_gbk.find('_section_strategy')
        print(f"  context: {repr(content_gbk[idx-20:idx+60])}")
    # Save GBK version
    with open(rp.replace('.py', '_gbk.py'), 'w', encoding='utf-8') as f:
        f.write(content_gbk)
    print("  Saved as _gbk.py (UTF-8)")
except Exception as e:
    print(f"GBK failed: {e}")

# Try UTF-8
try:
    with open(rp, 'r', encoding='utf-8', errors='replace') as f:
        content_utf8 = f.read()
    print(f"UTF-8(replace): size={len(content_utf8)}")
    has_strategy = '_section_strategy' in content_utf8
    print(f"  has _section_strategy: {has_strategy}")
    if has_strategy:
        idx = content_utf8.find('_section_strategy')
        print(f"  context: {repr(content_utf8[idx-20:idx+60])}")
except Exception as e:
    print(f"UTF-8 failed: {e}")
