"""Patch report.py to add investor_qa section"""
import re, ast

fpath = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'
content = open(fpath, encoding='utf-8').read()

# Step 1: Insert investor_qa section call (after institutional)
idx = content.find("    if 'institutional' in results['dims']:")
if idx == -1:
    print("ERROR: institutional section not found")
    exit(1)

insert = """    if 'investor_qa' in results['dims']:
        lines += _section_investor_qa(findings['investor_qa'])
"""
content = content[:idx] + insert + "\n" + content[idx:]
print("Step1: investor_qa section call inserted")

# Step 2: Add section function before _generate_timeline
new_func = '''
def _section_investor_qa(data):
    from scripts.investor_qa import format_markdown
    if not data:
        return ["## 二十三、投资者问答与互动分析\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["## 二十三、投资者问答与互动分析\\n\\n" + md]


'''

timeline_marker = "\ndef _generate_timeline(findings, path):"
content = content.replace(timeline_marker, new_func + timeline_marker)
print("Step2: investor_qa function appended")

# Step 3: Update unknown list
old_list = '    lines.append("- [ ] 精确盈利预测（需分析师行业判断）")'
if old_list in content:
    content = content.replace(old_list,
        '    lines.append("- [ ] 机构调研详细纪要（需下载PDF全文）")\n'
        '    lines.append("- [ ] 精确盈利预测（需分析师行业判断）')
    print("Step3: unknown list updated")

open(fpath, 'w', encoding='utf-8').write(content)

try:
    ast.parse(content)
    print("Syntax: PASS")
except SyntaxError as e:
    print(f"Syntax ERROR line {e.lineno}: {e.msg}")
