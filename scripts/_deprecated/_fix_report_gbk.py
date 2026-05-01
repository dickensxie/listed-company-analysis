"""Fix GBK corruption in report.py - binary replacement"""
import os

rp = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'

with open(rp, 'rb') as f:
    raw = f.read()

# The file is GBK encoded (from original). Fix:
# 1. Read as GBK to get the correct Chinese text
content_gbk = raw.decode('gbk')

# 2. Fix the corrupted lines by replacing them
# The corrupted section has garbage strings from UTF-8 write

# Find the _section_multi_year_trend function start
# and replace the whole section block

# Strategy: find the section functions section and rebuild it
# The functions start at "def _section_multi_year_trend"
# and end at "def _generate_timeline"

# Find markers
start_marker = '\ndef _section_multi_year_trend'
end_marker = '\ndef _generate_timeline(findings, path):'

idx_start = content_gbk.find(start_marker)
idx_end = content_gbk.find(end_marker)

print(f"Section start: {idx_start}, end: {idx_end}")

# Extract original content before sections
original_head = content_gbk[:idx_start]

# Build clean new sections
new_sections = '''

def _section_multi_year_trend(data):
    from scripts.multi_year_trend import format_markdown
    if not data:
        return ["## 十七、多年财务趋势\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["## 十七、多年财务趋势\\n\\n", md]


def _section_earnings_forecast(data):
    from scripts.earnings_forecast import format_markdown
    if not data:
        return ["## 十八、盈利预测\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["## 十八、盈利预测\\n\\n", md]


def _section_valuation(data):
    from scripts.valuation import format_markdown
    if not data:
        return ["## 十九、估值分析\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["## 十九、估值分析\\n\\n", md]


def _section_governance(data):
    from scripts.governance import format_markdown
    if not data:
        return ["## 二十、公司治理\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["## 二十、公司治理\\n\\n", md]


def _section_share_history(data):
    from scripts.share_history import format_markdown
    if not data:
        return ["## 二十一、股本与融资历史\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["## 二十一、股本与融资历史\\n\\n", md]


def _section_institutional(data):
    from scripts.institutional import format_markdown
    if not data:
        return ["## 二十二、机构持仓与筹码\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["## 二十二、机构持仓与筹码\\n\\n", md]


def _section_investor_qa(data):
    from scripts.investor_qa import format_markdown
    if not data:
        return ["## 二十三、投资者问答与互动分析\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["## 二十三、投资者问答与互动分析\\n\\n", md]


'''

# Extract content after _generate_timeline (the rest of the file)
rest_content = content_gbk[idx_end:]

# Also fix the corrupted _section_unknown in the head if needed
# Check for garbled lines around "精确盈利预测"
# The head contains _section_unknown which has corrupted GBK strings

# Find and fix _section_unknown in original_head
old_unknown_start = original_head.find('def _section_unknown(findings):')
if old_unknown_start != -1:
    # Find the end of _section_unknown (next def)
    next_def = original_head.find('\ndef ', old_unknown_start + 10)
    if next_def == -1:
        next_def = len(original_head)
    
    old_func = original_head[old_unknown_start:next_def]
    
    # Check if it has garbled content
    if any(ord(c) > 127 and c not in '\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef' for c in old_func[:200]):
        print("Found garbled _section_unknown, fixing...")
        # Build clean version
        new_func = '''def _section_unknown(findings):
    lines = []
    lines.append("")
    lines.append("## 二十三、信息缺失清单")
    lines.append("")
    lines.append("以下信息本次分析未能获取，建议手动补充：")
    lines.append("")
    lines.append("- [ ] 机构调研详细纪要（需下载PDF全文）")
    lines.append("- [ ] 精确盈利预测（需分析师行业判断）")
    lines.append("- [ ] 详细DCF参数（需分析师校正WACC/永续增长率）")
    lines.append("- [ ] 核心高管背景调查与详细履历")
    lines.append("- [ ] 最新股东名册与筹码分布细节")
    lines.append("- [ ] 竞争对手可比公司详细数据（如未公开）")
    lines.append("")
    return lines

'''
        original_head = original_head[:old_unknown_start] + new_func + original_head[next_def:]
        print("Fixed _section_unknown")
    else:
        print("_section_unknown appears OK, skipping")

# Write the combined result as UTF-8
new_content = original_head + new_sections + rest_content

with open(rp, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Written: {len(new_content)} chars")

# Syntax check
import ast
try:
    ast.parse(new_content)
    print("SYNTAX: PASS")
except SyntaxError as e:
    print(f"SYNTAX ERROR line {e.lineno}: {e.msg}")
    ln = new_content.split('\n')[e.lineno-1]
    print(f"  {ln[:120]}")
