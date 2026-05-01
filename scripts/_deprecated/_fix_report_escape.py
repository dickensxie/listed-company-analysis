"""Fix escaped newlines in report.py section function"""
fpath = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'
content = open(fpath, encoding='utf-8').read()

# Fix \\n -> \n in the investor_qa section
# Pattern: return ["## 二十三、投资者问答与互动分析\\n\\n" + md]
old = 'return ["## 二十三、投资者问答与互动分析\\\\n\\\\n" + md]'
new = 'return ["## 二十三、投资者问答与互动分析\\n\\n" + md]'

if old in content:
    content = content.replace(old, new)
    print(f"Fixed {content.count(new)} occurrence(s)")
else:
    print("Pattern not found, trying alternate...")
    # Find and fix all \\n in the section function
    import re
    # Replace \\n with \n within the _section_investor_qa function
    m = re.search(r'(def _section_investor_qa.*?return \[.*?\])', content, re.DOTALL)
    if m:
        fixed = m.group(1).replace('\\n', '\n')
        content = content[:m.start()] + fixed + content[m.end():]
        print("Fixed via regex")

open(fpath, 'w', encoding='utf-8').write(content)

# Syntax check
import ast
try:
    ast.parse(content)
    print("Syntax: PASS")
except SyntaxError as e:
    print(f"Syntax ERROR line {e.lineno}: {e.msg}")
    # Show context
    lines = content.split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+2)):
        print(f"  {i+1}: {lines[i]}")
