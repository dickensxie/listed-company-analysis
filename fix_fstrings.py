# -*- coding: utf-8 -*-
"""Fix broken f-strings in analyze.py"""
import re

path = r'C:\Users\Administrator\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\analyze.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix pattern: print(f"\n⚠️ or print(f"\n✅ etc - broken across lines
# The pattern is: print(f"\n<emoji_text>")
text = re.sub(r'print\(f"\n(.*?)\"\)', r'print(f"\1")', text)

# Also fix: print(f"\n<text>") pattern where text is on next line
# Find all unterminated f-strings
lines = text.split('\n')
fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check if this line has an unterminated f-string
    if 'print(f"' in line and line.rstrip().endswith('"'):
        # Check if next line starts the actual content
        if i + 1 < len(lines) and lines[i+1].strip() and not lines[i+1].strip().startswith('#'):
            next_line = lines[i+1].strip()
            # Merge: print(f"\n<content>") -> print(f"<content>")
            merged = line.rstrip()[:-1] + next_line + '")'
            if not merged.rstrip().endswith(')'):
                merged += ')'
            fixed_lines.append(merged)
            i += 2
            continue
    fixed_lines.append(line)
    i += 1

result = '\n'.join(fixed_lines)

with open(path, 'w', encoding='utf-8') as f:
    f.write(result)

# Verify syntax
try:
    compile(result, path, 'exec')
    print('✅ Syntax OK')
except SyntaxError as e:
    print(f'❌ Syntax error at line {e.lineno}: {e.msg}')
    # Show the problematic line
    err_lines = result.split('\n')
    if e.lineno and e.lineno <= len(err_lines):
        for j in range(max(0, e.lineno-3), min(len(err_lines), e.lineno+2)):
            print(f'  {j+1}: {err_lines[j]}')
