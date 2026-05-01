"""ASCII-only report.py patcher - no Chinese chars"""
import re, ast, os

RP = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'
TMP = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\_tmp_report.py'

with open(RP, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

print(f"File size: {len(content)} chars")

# Step 1: insert section calls before _section_strategy
target1 = "        lines += _section_strategy(stock, findings)"
insert1 = """        if 'multi_year_trend' in results['dims']:
            lines += _section_multi_year_trend(findings['multi_year_trend'])
        if 'earnings_forecast' in results['dims']:
            lines += _section_earnings_forecast(findings['earnings_forecast'])
        if 'valuation' in results['dims']:
            lines += _section_valuation(findings['valuation'])
        if 'governance' in results['dims']:
            lines += _section_governance(findings['governance'])
        if 'share_history' in results['dims']:
            lines += _section_share_history(findings['share_history'])
        if 'institutional' in results['dims']:
            lines += _section_institutional(findings['institutional'])
        if 'investor_qa' in results['dims']:
            lines += _section_investor_qa(findings['investor_qa'])
"""
if target1 in content:
    content = content.replace(target1, insert1 + target1)
    print("Step1: section calls OK")
else:
    print("Step1: target NOT FOUND")

# Step 2: append section functions before _generate_timeline
marker = "\ndef _generate_timeline(findings, path):"
new_funcs = '''
def _section_multi_year_trend(data):
    from scripts.multi_year_trend import format_markdown
    if not data:
        return ["\\n## 17-multi-year-trend [DATA_MISSING]\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 17-multi-year-trend\\n\\n", md]

def _section_earnings_forecast(data):
    from scripts.earnings_forecast import format_markdown
    if not data:
        return ["\\n## 18-earnings-forecast [DATA_MISSING]\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 18-earnings-forecast\\n\\n", md]

def _section_valuation(data):
    from scripts.valuation import format_markdown
    if not data:
        return ["\\n## 19-valuation [DATA_MISSING]\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 19-valuation\\n\\n", md]

def _section_governance(data):
    from scripts.governance import format_markdown
    if not data:
        return ["\\n## 20-governance [DATA_MISSING]\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 20-governance\\n\\n", md]

def _section_share_history(data):
    from scripts.share_history import format_markdown
    if not data:
        return ["\\n## 21-share-history [DATA_MISSING]\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 21-share-history\\n\\n", md]

def _section_institutional(data):
    from scripts.institutional import format_markdown
    if not data:
        return ["\\n## 22-institutional [DATA_MISSING]\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 22-institutional\\n\\n", md]

def _section_investor_qa(data):
    from scripts.investor_qa import format_markdown
    if not data:
        return ["\\n## 23-investor-qa [DATA_MISSING]\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 23-investor-qa\\n\\n", md]

'''

if marker in content:
    content = content.replace(marker, new_funcs + marker)
    print("Step2: section functions appended")
else:
    print("Step2: marker NOT FOUND")

# Write
with open(RP, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Written: {len(content)} chars")

# Syntax check
try:
    ast.parse(content)
    print("SYNTAX: PASS")
except SyntaxError as e:
    print("SYNTAX ERROR line %d: %s" % (e.lineno, e.msg))
