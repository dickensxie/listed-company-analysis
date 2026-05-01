"""Rewrite section functions to avoid embedded \n in string literals"""
import re

fpath = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'
with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Find and replace each bad section function
# Pattern: return ["## xxx\n\n" + md] with embedded \n
# Fix: use separate list items instead

bad_patterns = [
    ('_section_multi_year_trend', '十七、多年财务趋势'),
    ('_section_earnings_forecast', '十八、盈利预测'),
    ('_section_valuation', '十九、估值分析'),
    ('_section_governance', '二十、公司治理'),
    ('_section_share_history', '二十一、股本与融资历史'),
    ('_section_institutional', '二十二、机构持仓与筹码'),
    ('_section_investor_qa', '二十三、投资者问答与互动分析'),
]

for func_name, title in bad_patterns:
    # Match the entire function with the bad return
    # The pattern: def _section_xxx(data): ... return ["## title\n\n" + md]
    # We want: def _section_xxx(data): ... return ["## title", "", md]
    pattern = r'(def ' + re.escape(func_name) + r'\(data\):.*?return \["## ' + re.escape(title) + r'\\n\\n" \+ md\])'
    # Simpler: just find the return line and fix it
    pass

# Actually let's just find ALL return ["## ... \n\n" patterns
import re
# Find all lines with embedded real newlines inside return statements
lines = content.split('\n')
fixed_lines = []
in_bad_func = False
for i, line in enumerate(lines):
    stripped = line.strip()
    # Detect bad return statements (contain literal \n inside a string)
    # They look like: return ["## 章节标题\n\n" + md]
    if 'return ["##' in line and '\\n\\n"' in line:
        # This is a bad line - fix the embedded newlines
        # Change "## title\n\n" to "## title" (split into separate list items)
        # The line format: return ["## xxx\n\n" + md]
        # Fix: return ["## xxx", "", md]
        m = re.match(r'^(\s*return \["## )(.+)(\\n\\n" \+ md\])$', line)
        if m:
            fixed = m.group(1) + m.group(2) + '", "", md]'
            fixed_lines.append(fixed)
            print(f"Fixed line {i+1}: {fixed[:80]}")
            continue
    fixed_lines.append(line)

new_content = '\n'.join(fixed_lines)

# Check if we fixed anything
if new_content == content:
    print("WARNING: No changes made - pattern may not match")
    # Try a simpler approach: find lines with \n\\n" in them
    for i, line in enumerate(lines):
        if '\\n\\n"' in line or ('return ["##' in line and '\\n' in line):
            print(f"LINE {i+1}: {repr(line[:100])}")
else:
    print("Changes applied")
    # Write back
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("File written")

# Syntax check
import ast
try:
    ast.parse(new_content)
    print("SYNTAX: PASS")
except SyntaxError as e:
    print(f"SYNTAX ERROR line {e.lineno}: {e.msg}")
    ln = new_content.split('\n')[e.lineno-1]
    print(f"  {ln[:120]}")
