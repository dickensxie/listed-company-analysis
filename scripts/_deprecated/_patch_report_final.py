"""Patch report.py cleanly - add 7 new section functions and their calls"""
import re

rp = r'C:\Users\dicke\.qclaw\workspace-agent-550df5d1\skills\listed-company-analysis\scripts\report.py'
with open(rp, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# STEP 1: Insert section calls before _section_strategy
# ============================================================
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
assert target in content, "Target not found"
content = content.replace(target, insert + target)
print("Step1: section calls inserted")

# ============================================================
# STEP 2: Update _section_unknown info list
# ============================================================
old_list = """    lines.append("- [ ] 年报PDF全文（财务数据）")
    lines.append("- [ ] 诉讼/仲裁案的具体金额和进展")
    lines.append("- [ ] 高管辞职的真实原因")
    lines.append("- [ ] 子公司IPO辅导报告全文")
    lines.append("- [ ] 港股私有化要约的具体条款（收购价格、条件）")
    lines.append("- [ ] 问询函的详细内容")
    lines.append("- [ ] 独董核查意见全文")"""

new_list = """    lines.append("- [ ] 机构调研详细纪要（需下载PDF全文）")
    lines.append("- [ ] 精确盈利预测（需分析师行业判断）")
    lines.append("- [ ] 详细DCF参数（需分析师校正WACC/永续增长率）")
    lines.append("- [ ] 核心高管背景调查与详细履历")
    lines.append("- [ ] 最新股东名册与筹码分布细节")
    lines.append("- [ ] 竞争对手可比公司详细数据（如未公开）")"""

if old_list in content:
    content = content.replace(old_list, new_list)
    print("Step2: unknown list updated")
else:
    print("Step2: old list not found (may already be updated)")

# ============================================================
# STEP 3: Append new section functions before _generate_timeline
# ============================================================
marker = "\ndef _generate_timeline(findings, path):"

new_funcs = '''
def _section_multi_year_trend(data):
    from scripts.multi_year_trend import format_markdown
    if not data:
        return ["\\n## 十七、多年财务趋势\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 十七、多年财务趋势\\n\\n", md]


def _section_earnings_forecast(data):
    from scripts.earnings_forecast import format_markdown
    if not data:
        return ["\\n## 十八、盈利预测\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 十八、盈利预测\\n\\n", md]


def _section_valuation(data):
    from scripts.valuation import format_markdown
    if not data:
        return ["\\n## 十九、估值分析\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 十九、估值分析\\n\\n", md]


def _section_governance(data):
    from scripts.governance import format_markdown
    if not data:
        return ["\\n## 二十、公司治理\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 二十、公司治理\\n\\n", md]


def _section_share_history(data):
    from scripts.share_history import format_markdown
    if not data:
        return ["\\n## 二十一、股本与融资历史\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 二十一、股本与融资历史\\n\\n", md]


def _section_institutional(data):
    from scripts.institutional import format_markdown
    if not data:
        return ["\\n## 二十二、机构持仓与筹码\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 二十二、机构持仓与筹码\\n\\n", md]


def _section_investor_qa(data):
    from scripts.investor_qa import format_markdown
    if not data:
        return ["\\n## 二十三、投资者问答与互动分析\\n\\n_暂无数据_\\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\\n## 二十三、投资者问答与互动分析\\n\\n", md]


'''

assert marker in content, "_generate_timeline marker not found"
content = content.replace(marker, new_funcs + marker)
print("Step3: 7 new section functions appended")

# Write back
with open(rp, 'w', encoding='utf-8') as f:
    f.write(content)
print("File written")

# Syntax check
import ast
try:
    ast.parse(content)
    print("SYNTAX: PASS")
except SyntaxError as e:
    print("SYNTAX ERROR line %d: %s" % (e.lineno, e.msg))
