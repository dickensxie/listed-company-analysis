"""Patch report.py Step1 - insert section calls"""
import ast

RP = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'
with open(RP, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Insert BEFORE _section_strategy
target = "        lines += _section_strategy(stock, findings)"
insert = """        if 'multi_year_trend' in results['dims']:
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

if target in content:
    content = content.replace(target, insert + "\n" + target)
    print("Step1: inserted OK")
else:
    # Try without leading spaces
    alt = "lines += _section_strategy(stock, findings)"
    if alt in content:
        # Add proper indentation
        content = content.replace(alt, insert + "\n        " + alt)
        print("Step1: inserted (alt) OK")
    else:
        print("Step1: NOT FOUND")
        print("Content around line 94:")
        lines = content.split('\n')
        for i in range(90, 98):
            print(f"  {i+1}: {repr(lines[i][:80])}")

with open(RP, 'w', encoding='utf-8') as f:
    f.write(content)

try:
    ast.parse(content)
    print("SYNTAX: PASS")
except SyntaxError as e:
    print("SYNTAX ERROR line %d: %s" % (e.lineno, e.msg))
