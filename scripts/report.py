# -*- coding: utf-8 -*-
"""
模块10：报告生成
生成结构化Markdown分析报告（中文）
"""
import sys, json, os, re
import os as _os
# 确保 scripts/ 在模块搜索路径中（report.py 被 analyze.py 导入时工作目录为父目录）
_scripts_dir = _os.path.dirname(_os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

_SOURCE_LABELS_DISPLAY = {
    'em_api': '🌐 东方财富API',
    'em_announce': '🌐 东方财富公告API',
    'cninfo_api': '🌐 巨潮资讯API',
    'cninfo_hk_announce': '🌐 巨潮资讯港股公告',
    'csrc': '🌐 证监会辅导数据',
    'csrc_ak': '🌐 证监会辅导数据(AKShare)',
    'akshare': '🌐 AKShare封装',
    'akshare_hk_fin': '🌐 AKShare港股财务',
    'cninfo_pdf': '📄 巨潮资讯PDF',
    'sse': '📄 上交所官网',
    'szse': '📄 深交所官网',
    'bse_cn': '📄 北交所官网',
    'hkex_pw': '🌐 港交所披露易(Playwright)',
    'hkex': '🌐 港交所披露易',
    'sec_edgar': '🌐 SEC EDGAR',
    'yfinance': '🌐 Yahoo Finance',
    'annual_pdf_text': '📄 年报PDF文本提取',
    'local_pdf': '📁 本地PDF',
    'local_cache': '💾 本地缓存',
    'manual': '✍️ 手动输入',
    'all_failed': '❌ 全部失败',
    'unknown': '❓ 未知来源',
}

def _section_data_sources(traces):
    """生成数据来源溯源表章节"""
    lines = []
    lines.append("## 📋 数据来源溯源表")
    lines.append("")
    lines.append("| 数据维度 | 数据来源 | 状态 | 备注 |")
    lines.append("|----------|----------|------|------|")
    for t in traces:
        icon = '✅' if t['status'] == 'OK' else '❌'
        src = t.get('source', 'unknown')
        src_label = _SOURCE_LABELS_DISPLAY.get(src, src)
        pdf_note = ''
        if t.get('pdf_source') and t['pdf_source'] not in ('all_failed', 'unknown'):
            pdf_note = f"(PDF: {_SOURCE_LABELS_DISPLAY.get(t['pdf_source'], t['pdf_source'])})"
        msg = t.get('msg', '')
        if len(msg) > 60:
            msg = msg[:57] + '...'
        lines.append(f"| {t['dim_label']} | {src_label} {pdf_note} | {icon} | {msg} |")
    lines.append("")
    failed = [t for t in traces if t['status'] == 'FAIL']
    if failed:
        lines.append(f"⚠️ **有 {len(failed)} 个数据维度获取失败**，可能影响分析完整性。\n")
        for t in failed:
            lines.append(f"- **{t['dim_label']}**（{t['source_label']}）: {t.get('msg', '')}")
        lines.append("")
    return lines

def generate_report(results, out_dir):
    """生成完整分析报告"""
    stock = results['stock']
    market = results['market']
    market_name = {'a': 'A股', 'hk': '港股', 'us': '美股'}.get(market, 'A股')
    findings = results['findings']
    date = results['date']

    lines = []
    lines.append(f"# {stock} {market_name} 全景分析报告")
    lines.append(f"")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ")
    lines.append(f"**股票代码**: {stock}  ")
    lines.append(f"**分析维度**: {', '.join(results['dims'])}  ")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ==================== 第一部分：数据来源溯源 ====================
    if results.get('_traces'):
        lines += _section_data_sources(results['_traces'])

    # ==================== 第二部分：执行摘要 ====================
    lines += _section_executive_summary(stock, findings)

    # ==================== 第二部分：公告全景 ====================
    if 'announcements' in results['dims']:
        lines += _section_announcements(findings['announcements'])

    # ==================== 实时行情 ====================
    if 'quote' in results['dims'] and 'quote' in findings:
        lines += _section_quote(findings['quote'])

    # ==================== 第三部分：财务报表 ====================
    if 'financial' in results['dims']:
        lines += _section_financial(findings['financial'])

    # 港股财务（替代A股财务报表）
    if 'hk_financial' in results['dims']:
        lines += _section_hk_financial(findings['hk_financial'])

    # 港交所公告（Playwright自动化）
    if 'hkex_announcements' in results['dims'] and 'hkex_announcements' in findings:
        lines += _section_hkex_announcements(findings['hkex_announcements'])

    # ==================== 第四部分：高管动态 ====================
    if 'executives' in results['dims']:
        lines += _section_executives(findings['executives'])

    # ==================== 第五部分：资金动作 ====================
    if 'capital' in results['dims']:
        lines += _section_capital(findings['capital'])

    # ==================== 第六部分：子公司IPO ====================
    if 'subsidiary' in results['dims']:
        lines += _section_subsidiary(findings['subsidiary'])

    # ==================== 第七部分：关联方资本运作 ====================
    if 'related' in results['dims']:
        lines += _section_related(findings['related'])

    # ==================== 第八部分：监管历史 ====================
    if 'regulatory' in results['dims']:
        lines += _section_regulatory(findings['regulatory'])

    # ==================== 第九部分：股权结构 ====================
    if 'structure' in results['dims']:
        lines += _section_structure(findings['structure'])

    # ==================== 第十部分：行业竞争格局 ====================
    if 'industry' in results['dims']:
        lines += _section_industry(findings['industry'])

    # ==================== 新增深度分析章节（原bug：定义了但从未调用）====================
    if 'multi_year_trend' in results['dims']:
        lines += _section_multi_year_trend(findings.get('multi_year_trend'))
    if 'valuation' in results['dims']:
        lines += _section_valuation(findings.get('valuation'))
    if 'earnings_forecast' in results['dims']:
        lines += _section_earnings_forecast(findings.get('earnings_forecast'))
    if 'governance' in results['dims']:
        lines += _section_governance(findings.get('governance'))
    if 'share_history' in results['dims']:
        lines += _section_share_history(findings.get('share_history'))
    if 'institutional' in results['dims']:
        lines += _section_institutional(findings.get('institutional'))
    if 'investor_qa' in results['dims']:
        lines += _section_investor_qa(findings.get('investor_qa'))

    # ==================== 第十一部分：同业财务对比 ====================
    if 'peer_compare' in results['dims']:
        lines += _section_peer_compare(findings['peer_compare'])

    # ==================== 第十二部分：研发与利润归因 ====================
    if 'rd_analysis' in results['dims']:
        lines += _section_rd_analysis(findings['rd_analysis'])

    # ==================== 第十三部分：风险评级 ====================
    if 'risk' in results['dims']:
        lines += _section_risk(findings['risk'])

    # ==================== 第十三点五部分：跨维度交叉验证（隐情发现） ====================
    if 'cross_validation' in results['dims'] and 'cross_validation' in findings:
        lines += _section_cross_validation(findings['cross_validation'])

    # ==================== 第十四部分：战略意图分析 ====================
    lines += _section_strategy(stock, findings)

    # ==================== 第十五部分：投资逻辑 ====================
    try:
        from scripts.investment_thesis import generate_investment_thesis
        thesis = generate_investment_thesis(results, stock, market)
        lines.append(thesis['markdown'])
        lines.append("")
    except Exception as e:
        lines.append("## 投资逻辑")
        lines.append("")
        lines.append(f"投资逻辑生成失败: {e}")
        lines.append("")

    # ==================== 第十六部分：盈利预测与估值 ====================
    if 'earnings_forecast' in results['dims']:
        lines += _section_earnings_forecast(findings.get('earnings_forecast'))

    # ==================== 第十七部分：可视化图表 ====================
    if 'charts' in findings and findings['charts']:
        lines.append("## 可视化分析")
        lines.append("")
        from scripts.visualization import charts_to_markdown
        chart_md = charts_to_markdown(findings['charts'], out_dir)
        lines.append(chart_md)
        lines.append("")

    # ==================== 第十八部分：年报PDF分析 ====================
    if 'annual_pdf' in results['dims']:
        lines += _section_annual_pdf(findings['annual_pdf'])

    # ==================== 第十九部分：信息缺失清单 ====================
    lines += _section_unknown(findings)

    report_text = '\n'.join(lines)

    # 自动修正章节编号：按出现顺序从「一」开始连续编号
    import re
    cn_nums = ['一','二','三','四','五','六','七','八','九','十','十一','十二','十三','十四','十五','十六','十七','十八','十九','二十']
    idx = 0
    def _renum(m):
        nonlocal idx
        if idx < len(cn_nums):
            s = cn_nums[idx]
            idx += 1
            return f'## {s}、'
        return m.group(0)
    report_text = re.sub(r'^## [一二三四五六七八九十]+、', _renum, report_text, flags=re.MULTILINE)

    report_path = os.path.join(out_dir, 'report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # 生成事件时间线
    timeline_path = os.path.join(out_dir, 'timeline.md')
    _generate_timeline(findings, timeline_path)

    # 生成风险清单
    warnings_path = os.path.join(out_dir, 'warnings.md')
    _generate_warnings(findings, warnings_path)

    return report_path


# ==================== 各部分生成函数 ====================

def _section_executive_summary(stock, findings):
    lines = []
    lines.append("## 一、执行摘要")
    lines.append(f"")
    lines.append(f"**股票代码**: {stock}")
    lines.append(f"")

    # 风险等级
    risk = findings.get('risk', {})
    if risk:
        lines.append(f"**综合风险等级**: {risk.get('level', '未知')}（{risk.get('score', 0)}/100）")
        lines.append(f"")

    # 关键发现
    high_risk = risk.get('summary', {}).get('high_risk', [])
    if high_risk:
        lines.append("**⚠️ 高风险信号**:")
        for s in high_risk[:5]:
            lines.append(f"- [{s['dim']}] {s['detail']}")
        lines.append(f"")

    # 子公司IPO状态
    sub = findings.get('subsidiary', {})
    if sub.get('subsidiaries'):
        subs = sub['subsidiaries']
        lines.append(f"**子公司分拆/IPO**: {len(subs)}项筹划中")
        for s in subs[:3]:
            lines.append(f"- {s.get('date','')} {s.get('sub_company','子公司')} → {s.get('target_board','未知板块')}")
        lines.append(f"")

    # 财务状态
    fin = findings.get('financial', {})
    if fin.get('audit_opinion'):
        lines.append(f"**审计意见**: {fin['audit_opinion']}")
        if fin.get('key_risks'):
            for r in fin['key_risks'][:3]:
                lines.append(f"- {r}")
        lines.append(f"")

    # 同业对比亮点
    peer = findings.get('peer_compare', {})
    if peer.get('has_data') and peer.get('peer_count', 0) > 0:
        conc = peer.get('conclusion', '')
        if conc:
            lines.append(f"**同业对比亮点**: {conc}")
        target = peer.get('target', {})
        stats = peer.get('stats', {})
        advantages = []
        for key, label in (('roe', 'ROE'), ('gross_margin', '毛利率'), ('revenue_growth', '营收增速')):
            tv = target.get(key)
            mv = stats.get(key, {}).get('mean')
            if tv is not None and mv and mv > 0 and tv > mv * 1.5:
                ratio = tv / mv
                if ratio >= 3:
                    advantages.append(f"{label}(均值{int(ratio)}倍)")
                elif ratio >= 2:
                    advantages.append(f"{label}(均值{ratio:.1f}x)")
                else:
                    advantages.append(f"{label}(超越均值{int((tv-mv)/mv*100)}%)")
        if advantages:
            lines.append(f"  核心优势: {', '.join(advantages)}")
        lines.append(f"")

    return lines


def _section_announcements(data):
    lines = []
    lines.append("## 二、公告全景（近12个月）")
    lines.append(f"")
    lines.append(f"**公告总数**: {data.get('count', 0)}条")
    
    # 重要性分级统计
    stats = data.get('importance_stats', {})
    if stats:
        lines.append(f"")
        lines.append(f"**重要性分级**: ")
        lines.append(f"- 🔴 CRITICAL（重大事项，已深挖）: {stats.get('critical', 0)}条")
        lines.append(f"- 🟡 MAJOR（较重要，关注动向）: {stats.get('major', 0)}条")
        lines.append(f"- 🟢 ROUTINE（常规披露）: {stats.get('routine', 0)}条")
    lines.append(f"")

    # 🔴 CRITICAL公告（含提取内容）
    critical = data.get('critical_announcements', [])
    if critical:
        lines.append("### 🔴 重大事项（CRITICAL）")
        lines.append(f"")
        for a in critical:
            tag = a.get('importance_tag', '')
            lines.append(f"#### {a.get('date','')[:10]} | {tag}")
            lines.append(f"{a.get('title','')[:100]}")
            # 关键事实
            content = a.get('extracted_content', {})
            if content and not content.get('error'):
                facts = content.get('key_facts', [])
                if facts:
                    lines.append(f"")
                    for f in facts:
                        lines.append(f"- {f}")
                pages = content.get('page_count', 0)
                if pages:
                    lines.append(f"")
                    lines.append(f"*PDF {pages}页，已提取关键内容*")
            lines.append(f"")

    # 🟡 MAJOR公告
    major = data.get('major_announcements', [])
    if major:
        lines.append("### 🟡 较重要事项（MAJOR）")
        lines.append(f"")
        for a in major[:15]:
            tag = a.get('importance_tag', '')
            lines.append(f"- **{a.get('date','')[:10]}** [{tag}] {a.get('title','')[:80]}")
        if len(major) > 15:
            lines.append(f"- ... 还有{len(major)-15}条MAJOR公告")
        lines.append(f"")

    # 📎 事件溯源链
    chains = data.get('event_chains', {})
    if chains:
        lines.append("### 📎 事件溯源链")
        lines.append(f"")
        lines.append("*重要事件追溯历史关联公告，理清来龙去脉*")
        lines.append(f"")
        for tag, chain in chains.items():
            chain_anns = chain.get('chain', [])
            origin = chain.get('origin')
            lines.append(f"#### {tag}（追溯{chain.get('chain_length',0)}条）")
            lines.append(f"")
            if origin:
                lines.append(f"**源头**: {origin.get('date','')[:10]} | {origin.get('title','')[:80]}")
                lines.append(f"")
            for a in chain_anns[:8]:
                lines.append(f"- {a.get('date','')[:10]} | {a.get('title','')[:80]}")
            lines.append(f"")

    # 兼容：分类统计（汇总）
    categories = data.get('categories', {})
    if categories:
        lines.append("### 分类统计")
        lines.append(f"")
        for cat, anns in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            lines.append(f"- {cat}: {len(anns)}条")
        lines.append(f"")

    # 兼容旧 key_events
    key_events = data.get('key_events', [])
    if key_events and not critical:
        lines.append("**重大事件清单**:")
        for e in key_events[:15]:
            lines.append(f"- **{e.get('date','')}** {e.get('title','')[:80]}")
        lines.append(f"")

    return lines


def _section_financial(data):
    lines = []
    lines.append("## 三、财务报表分析")
    lines.append(f"")

    lines.append(f"**审计意见**: {data.get('audit_opinion', '未知')}")
    lines.append(f"")

    # PDF fallback 数据渲染
    from_pdf = data.get('from_pdf_fallback', False)
    summary = data.get('summary', {})
    if summary:
        if from_pdf:
            lines.append("*📄 数据来源：年报PDF提取*")
        lines.append("")
        revenue = summary.get('revenue_亿')
        net_profit = summary.get('net_profit_亿')
        gross_margin = summary.get('gross_margin_pct')
        revenue_growth = summary.get('revenue_growth_pct')
        net_profit_growth = summary.get('net_profit_growth_pct')
        if revenue:
            lines.append(f"**营业收入**: {revenue}亿元")
        if net_profit:
            lines.append(f"**归母净利润**: {net_profit}亿元")
        if gross_margin:
            lines.append(f"**毛利率**: {gross_margin}%")
        if revenue_growth:
            lines.append(f"**营收增速**: {revenue_growth}%")
        if net_profit_growth:
            lines.append(f"**净利润增速**: {net_profit_growth}%")
        lines.append(f"")

    # 财务趋势表
    records = data.get('records', [])
    if records and len(records) >= 1:
        latest = data.get('latest', records[0])
        if latest:
            rdate = latest.get('REPORTDATE', '未知')
            lines.append(f"**最新报告期**: {rdate}")
            fields = {
                'TOTAL_OPERATE_INCOME': '营收(元)',
                'PARENT_NETPROFIT': '归母净利润(元)',
                'GROSS_PROFIT_RATIO': '毛利率(%)',
                'BASIC_EPS': '每股收益(元)',
                'WEIGHTAVG_ROE': '加权ROE(%)',
                'BPS': '每股净资产(元)',
            }
            for f, label in fields.items():
                v = latest.get(f)
                if v is not None and v != '':
                    if f in ('TOTAL_OPERATE_INCOME', 'PARENT_NETPROFIT'):
                        lines.append(f"- **{label}**: {round(float(v)/1e8, 2)}亿元")
                    elif f in ('BASIC_EPS', 'BPS'):
                        lines.append(f"- **{label}**: {round(float(v), 4)}")
                    else:
                        lines.append(f"- **{label}**: {v}")
            lines.append(f"")

    annual_reports = data.get('annual_reports', [])
    if annual_reports:
        lines.append("**近两年年报公告**:")
        for r in annual_reports[:4]:
            lines.append(f"- {r.get('date','')} {r.get('title','')[:80]}")
        lines.append(f"")

    # 财务风险
    key_risks = data.get('key_risks', [])
    if key_risks:
        lines.append("**⚠️ 财务风险信号**:")
        for r in key_risks:
            lines.append(f"- {r}")
        lines.append(f"")

    return lines


def _section_hk_financial(data):
    """港股财务章节"""
    lines = []
    lines.append("## 四、财务报表分析（港股）")
    lines.append("")
    
    # 基本面
    profile = data.get('profile', {})
    if profile:
        lines.append(f"**公司**: {profile.get('company_name_cn', '未知')} ({profile.get('industry', '')})")
        lines.append(f"**董事长**: {profile.get('chairman', '未知')} | **核数师**: {profile.get('auditor', '未知')}")
        lines.append(f"**员工**: {profile.get('employees', '未知')}人 | **注册地**: {profile.get('registered_place', '未知')}")
        lines.append("")
    
    # 估值
    valuation = data.get('valuation', {})
    if valuation:
        pe = valuation.get('pe_ttm')
        pb = valuation.get('pb')
        mc = valuation.get('market_cap')
        dy = valuation.get('dividend_yield')
        lines.append("**估值指标**:")
        lines.append(f"- 市值: {mc:,.0f} HKD" if mc else "- 市值: 未知")
        lines.append(f"- PE: {pe:.1f}x (亏损)" if pe and pe < 0 else f"- PE: {pe:.1f}x" if pe else "- PE: 未知")
        lines.append(f"- PB: {pb:.2f}x" if pb else "- PB: 未知")
        lines.append(f"- 股息率: {dy:.2f}%" if dy else "- 股息率: 未知")
        lines.append("")
    
    # 财务指标（最新一期）
    indicators = data.get('indicators', [])
    if indicators:
        lat = indicators[0]
        prev = indicators[1] if len(indicators) > 1 else {}
        lines.append("**财务指标（最新一期）**:")
        lines.append(f"- 报告期: {lat.get('date', '未知')} | 币种: {lat.get('currency', 'HKD')}")
        lines.append(f"- 营收: {lat.get('operate_income'):,.0f} HKD (同比: {lat.get('income_yoy'):+.1f}%)" if lat.get('operate_income') else "- 营收: 未知")
        lines.append(f"- 毛利: {lat.get('gross_profit'):,.0f} HKD | 毛利率: {lat.get('gross_margin'):.1f}%" if lat.get('gross_margin') else "- 毛利: 未知")
        lines.append(f"- 归母净利润: {lat.get('holder_profit'):,.0f} HKD" if lat.get('holder_profit') else "- 归母净利润: 未知")
        lines.append(f"- ROE: {lat.get('roe'):.1f}%" if lat.get('roe') else "- ROE: 未知")
        lines.append(f"- 资产负债率: {lat.get('debt_asset_ratio'):.1f}%" if lat.get('debt_asset_ratio') else "- 资产负债率: 未知")
        lines.append("")
        
        # 多期对比
        if len(indicators) > 1:
            show_count = len(indicators)
            lines.append(f"**近{show_count}年财务趋势**:")
            lines.append("| 报告期 | 营收(HKD) | 同比 | 毛利率 | 归母净利润 | ROE | 资产负债率 |")
            lines.append("|--------|-----------|------|--------|-----------|-----|----------|")
            for r in indicators:
                oi = f"{r.get('operate_income',0)/1e8:,.0f}亿" if r.get('operate_income') else "N/A"
                yoy = f"{r.get('income_yoy',0):+.1f}%" if r.get('income_yoy') is not None else "N/A"
                gm = f"{r.get('gross_margin',0):.1f}%" if r.get('gross_margin') else "N/A"
                hp = f"{r.get('holder_profit',0)/1e8:,.0f}亿" if r.get('holder_profit') else "N/A"
                roe = f"{r.get('roe',0):.1f}%" if r.get('roe') else "N/A"
                dar = f"{r.get('debt_asset_ratio',0):.1f}%" if r.get('debt_asset_ratio') else "N/A"
                lines.append(f"| {r.get('date','?')} | {oi} | {yoy} | {gm} | {hp} | {roe} | {dar} |")
            lines.append("")
    
    # 分红
    dividend = data.get('dividend', [])
    if dividend:
        lines.append("**分红历史**:")
        for d in dividend[:4]:
            lines.append(f"- {d.get('fiscal_year','?')} | {d.get('plan','?')} | 除净日: {d.get('ex_date','?')}")
        lines.append("")
    
    # 风险信号
    analysis = data.get('analysis', {})
    warnings = analysis.get('warnings', []) or data.get('warnings', [])
    if warnings:
        lines.append("**⚠️ 风险信号**:")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")
    
    return lines


def _section_executives(data):
    lines = []
    lines.append("## 五、高管动态")
    lines.append(f"")

    changes = data.get('changes', [])
    summary = data.get('summary', {})

    lines.append(f"**高管变动总数**: {len(changes)}条")
    lines.append(f"")

    if summary.get('warnings'):
        lines.append("**⚠️ 风险提示**:")
        for w in summary['warnings']:
            lines.append(f"- {w}")
        lines.append(f"")

    if changes:
        lines.append("**变动明细**:")
        for c in changes[:15]:
            lines.append(f"- **{c.get('date','')}** [{c.get('type','')}] {c.get('title','')[:80]}")
        lines.append(f"")

    incentives = data.get('equity_incentives', [])
    if incentives:
        lines.append("**股权激励事项**:")
        for i in incentives[:10]:
            lines.append(f"- **{i.get('date','')}** [{i.get('type','')}] {i.get('title','')[:80]}")
        lines.append(f"")

    return lines


def _section_capital(data):
    lines = []
    lines.append("## 六、资金动作分析")
    lines.append(f"")
    lines.append(f"**资金动作总数**: {data.get('count', 0)}项")
    lines.append(f"")

    actions = data.get('actions', [])
    if actions:
        lines.append("**动作明细**:")
        for a in actions[:20]:
            risk = f" → {a.get('risk_signal','')}" if a.get('risk_signal') else ''
            lines.append(f"- **{a.get('date','')}** [{a.get('type','')}] {a.get('title','')[:70]}{risk}")
        lines.append(f"")

    return lines


def _section_subsidiary(data):
    lines = []
    lines.append("## 七、子公司分拆/IPO追踪")
    lines.append(f"")

    subs = data.get('subsidiaries', [])
    csrc = data.get('csrc_tutoring', [])  # 现在是list
    report_count = data.get('report_count', '未知')
    tutoring_total = data.get('tutoring_total', 0)

    if subs:
        lines.append("**分拆上市公告**:")
        for s in subs:
            lines.append(f"- **{s.get('date','')}** {s.get('title','')[:90]}")
            lines.append(f"  - 子公司: {s.get('sub_company','未知')} | 目标板块: {s.get('target_board','未知')}")
        lines.append(f"")

    if csrc and len(csrc) > 0:
        lines.append(f"**证监会辅导备案**（共{tutoring_total}条，当前{report_count}）:")
        for item in csrc[:5]:
            name = item.get('company_name', '')
            status = item.get('status', '')
            rtype = item.get('report_type', '')
            org = item.get('tutor_org', '')
            date = item.get('filing_date', '')[:10]
            lines.append(f"- {date} | {name} | {status} | {rtype} | 辅导机构:{org}")
        if len(csrc) > 5:
            lines.append(f"  - ...还有{len(csrc)-5}条")
        lines.append(f"")

    findings = data.get('findings', [])
    if findings:
        lines.append("**IPO进度评估**:")
        for f in findings:
            level_icon = {'high': '🔴', 'medium': '🟡', 'info': '🟢'}.get(f.get('level',''), '⚪')
            lines.append(f"- {level_icon} {f.get('text','')}")
        lines.append(f"")

    if not subs and not csrc:
        lines.append("> 近12个月公告中未找到分拆上市相关公告，AKShare辅导数据中也未找到相关记录。")
        lines.append(f"")

    return lines


def _section_related(data):
    lines = []
    lines.append("## 八、关联方资本运作")
    lines.append(f"")
    lines.append(f"**资本运作总数**: {data.get('count', 0)}项")
    lines.append(f"")

    deals = data.get('deals', [])
    if deals:
        lines.append("**运作明细**:")
        for d in deals:
            risk = f" ⚠️ {d.get('risk','')}" if d.get('risk') else ''
            lines.append(f"- **{d.get('date','')}** [{d.get('type','')}] {d.get('title','')[:70]}{risk}")
        lines.append(f"")

    # 港股私有化
    go_private = data.get('go_private', [])
    if go_private:
        lines.append("**⚠️ 港股私有化**:")
        for gp in go_private:
            lines.append(f"- **{gp.get('date','')}** {gp.get('title','')[:80]}")
            if gp.get('offeror'):
                lines.append(f"  - 要约人/收购方: {gp['offeror']}")
            if gp.get('advisor'):
                lines.append(f"  - 财务顾问: {gp['advisor']}")
            if gp.get('deadline'):
                lines.append(f"  - 截止日期: {gp['deadline']}")
        lines.append(f"")

    summary = data.get('summary', {})
    if summary.get('by_type'):
        lines.append("**类型统计**:")
        for t, cnt in summary['by_type'].items():
            lines.append(f"- {t}: {cnt}项")
        lines.append(f"")

    return lines


def _section_regulatory(data):
    lines = []
    lines.append("## 九、监管历史追溯")
    lines.append(f"")
    lines.append(f"**监管记录总数**: {data.get('count', 0)}条")
    lines.append(f"")

    summary = data.get('summary', {})
    if summary.get('by_severity'):
        lines.append("**严重程度分布**:")
        for sev, cnt in summary['by_severity'].items():
            lines.append(f"- {sev}: {cnt}条")
        lines.append(f"")

    records = data.get('records', [])
    if records:
        lines.append("**监管记录明细**:")
        for r in records[:20]:
            lines.append(f"- **{r.get('date','')}** {r.get('severity','')} [{r.get('type','')}] {r.get('title','')[:70]}")
        lines.append(f"")

    return lines


def _section_structure(data):
    lines = []
    lines.append("## 十、股权结构分析")
    lines.append(f"")
    text = data.get('text', '')
    if text:
        lines.append("```")
        lines.append(text)
        lines.append("```")
        lines.append(f"")
    else:
        lines.append("> 股权结构信息有限，需结合年报或工商信息补充。")
        lines.append(f"")
    return lines


def _section_industry(data):
    lines = []
    lines.append("## 十、行业竞争格局")
    lines.append("")
    ib = data.get('industry_class', {})
    if ib:
        csrc = ib.get('csrc_industry', '未知')
        sw = ib.get('sw_industry', ib.get('sw_industry_l1', ''))
        board = ib.get('board_l2', '')
        region = ib.get('region', '')
        lines.append(f"**证监会行业**: {csrc or '未知'}")
        if sw:
            lines.append(f"**申万行业**: {sw}")
        if board:
            lines.append(f"**板块**: 计算机 > {board}")
        if region:
            lines.append(f"**地域**: {region}")
    else:
        lines.append("> 行业分类数据暂缺")
    lines.append("")

    # 主营构成
    income = data.get('income_structure', [])
    if income:
        lines.append("**主营构成**（收入占比）:")
        for item in income[:6]:
            ratio = f"({item['ratio']})" if item.get('ratio') else ""
            lines.append(f"- {item['product']} {ratio}")
        lines.append("")

    # 毛利率
    gp = data.get('findings', {}).get('gross_profit_ratio')
    if gp:
        lines.append(f"**毛利率**: {gp}%（原装打印机及耗材驱动）")
        lines.append("")

    # 概念板块
    concepts = data.get('findings', {}).get('concepts', [])
    if concepts:
        sample = [c for c in concepts if c][:10]
        lines.append(f"**概念板块**: {', '.join(sample)}")
        lines.append("")

    # 可比公司
    competitors = data.get('competitors', [])
    if competitors:
        lines.append(f"**主要可比公司**（{len(competitors)}家）:")
        for c in competitors[:6]:
            note = f" — {c.get('note','')}" if c.get('note') else ''
            src = "" if c.get('data_source') == '知识库补充' else f" [{c.get('data_source','')}]"
            lines.append(f"- {c.get('code','')} {c.get('name','')}{note}{src}")
        lines.append("")

    # 市场地位
    mp = data.get('market_position')
    if mp:
        lines.append(f"**市场地位**: {mp}")
        lines.append("")

    # 风险信号
    risks = data.get('risks', [])
    if risks:
        lines.append("**风险信号**:")
        for r in risks:
            lines.append(f"- [{r.get('level','?')}] {r.get('signal','')}")
        lines.append("")

    # 说明
    warnings = data.get('warnings', [])
    if warnings:
        lines.append("**⚠️ 说明**:")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    return lines


def _section_risk(data):
    lines = []
    lines.append("## 十三、综合风险评级")
    lines.append(f"")
    lines.append(f"**风险得分**: {data.get('score', 0)}/100")
    lines.append(f"")
    lines.append(f"**风险等级**: {data.get('level', '未知')}")
    lines.append(f"")

    signals = data.get('signals', [])
    if signals:
        lines.append("**风险信号明细**:")
        for s in signals:
            lines.append(f"- {s.get('level','')} **[{s.get('dim','')}]** {s.get('detail','')}")
        lines.append(f"")

    high = data.get('summary', {}).get('high_risk', [])
    medium = data.get('summary', {}).get('medium_risk', [])
    if high:
        lines.append(f"**🔴 高风险信号 ({len(high)}项)**:")
        for s in high:
            lines.append(f"- {s['detail']}")
        lines.append(f"")
    if medium:
        lines.append(f"**🟡 中风险信号 ({len(medium)}项)**:")
        for s in medium:
            lines.append(f"- {s['detail']}")
        lines.append(f"")

    return lines


def _section_cross_validation(data):
    """跨维度交叉验证隐情发现报告"""
    lines = []
    lines.append("## 十三.五、🔍 跨维度交叉验证：隐情发现")
    lines.append(f"")

    summary = data.get('summary', {})
    score = summary.get('score', 0)
    overall = summary.get('overall', '未知')
    lines.append(f"**隐情评分**: {score}/100 | {overall}")
    lines.append(f"")
    lines.append(f"> 每条隐情均由≥2个独立维度信号支撑。隐情发现不等同于事实认定，仅为投资研究参考。")
    lines.append(f"")

    hidden_truths = data.get('hidden_truths', [])
    if not hidden_truths:
        lines.append(f"🟢 **暂无重大隐情** — 各维度交叉验证未发现显著异常组合。单维度预警请参考风险评级章节。")
        lines.append(f"")
        return lines

    for t in hidden_truths:
        lines.append(f"### {t['level']} {t['category']} → {t['type']}")
        lines.append(f"")
        lines.append(t.get('narrative', ''))
        lines.append(f"")
        lines.append(f"<details><summary>支撑信号（{t['signal_count']}个）</summary>")
        lines.append(f"")
        for sig in t.get('signals', []):
            icon = {'strong': '🔴', 'medium': '🟠', 'weak': '🟡'}.get(sig['strength'], '⚪')
            lines.append(f"- {icon} [{sig['dim']}] {sig['detail']}")
        lines.append(f"")
        lines.append(f"</details>")
        lines.append(f"")

    return lines


def _section_strategy(stock, findings):
    lines = []
    lines.append("## 十四、战略意图综合分析")
    lines.append(f"")
    lines.append(f"**股票**: {stock}")
    lines.append(f"")
    lines.append("**逻辑推断**（基于已确认事实）:")
    lines.append(f"")
    lines.append("> 本节基于已确认的公告信息进行逻辑推断，不代表确定结论。")
    lines.append(f"")

    # 从各维度发现推断战略意图
    subs = findings.get('subsidiary', {}).get('subsidiaries', [])
    related = findings.get('related', {}).get('deals', [])
    go_private = findings.get('related', {}).get('go_private', [])
    fin_risks = findings.get('financial', {}).get('key_risks', [])

    # 判断1：分拆IPO
    if subs:
        lines.append(f"**1. 子公司IPO动向**:")
        for s in subs:
            lines.append(f"   - {s.get('date','')}: {s.get('title','')[:80]}")
        lines.append(f"")

    # 判断2：关联方整合
    if go_private:
        lines.append(f"**2. 关联方私有化/收购**:")
        for gp in go_private:
            lines.append(f"   - {gp.get('date','')}: {gp.get('title','')[:80]}")
            if gp.get('offeror'):
                lines.append(f"     - 收购方: {gp['offeror']}")
        lines.append(f"")

    # 判断3：财务困境与资本运作的关联
    if fin_risks:
        lines.append(f"**3. 财务压力信号**:")
        for r in fin_risks:
            lines.append(f"   - {r}")
        lines.append(f"")

    # 综合推断（基于各维度发现的实质性结论）
    lines.append(f"**综合推断**（谨慎结论）:")
    lines.append(f"")
    lines.append(f"> 基于上述发现，上市公司的资本运作呈现以下特征:")
    
    # 自动生成推断结论
    insights = []
    
    # 推断1：资本运作节奏
    if subs:
        insights.append(f"**分拆上市进程活跃**：近12个月{len(subs)}项子公司分拆/IPO公告，显示上市公司正在推进资产分拆和独立融资。")
    if go_private:
        insights.append(f"**关联方整合加速**：港股私有化/关联收购动作频繁，可能是在为整体上市或资产注入扫清障碍。")
    
    # 推断2：财务压力与融资需求
    if fin_risks:
        risk_text = "; ".join(fin_risks[:2])
        insights.append(f"**财务压力显现**：{risk_text}，这可能是资本运作频繁的直接动因。")
    
    # 推断3：治理与风险信号
    reg_records = findings.get('regulatory', {}).get('records', [])
    exec_changes = findings.get('executives', {}).get('changes', [])
    if reg_records:
        severe = [r for r in reg_records if '警示' in r.get('severity', '') or '处罚' in r.get('severity', '')]
        if severe:
            insights.append(f"**监管风险需关注**：近12个月有{len(severe)}项监管处罚/警示，合规风险上升。")
    if len(exec_changes) > 3:
        insights.append(f"**高管层不稳定**：近12个月{len(exec_changes)}次高管变动，需关注管理层稳定性。")
    
    # 补充默认推断（如果推断不足3条）
    if len(insights) < 3:
        if not subs and not go_private:
            insights.append("**资本运作相对沉寂**：近12个月未见重大分拆、私有化等资本运作公告，可能处于战略调整期。")
        if not fin_risks:
            insights.append("**财务状况平稳**：未发现明显财务风险信号，基本面相对健康。")
    
    # 输出推断（确保至少3条）
    for i, insight in enumerate(insights[:5], 1):
        lines.append(f"> {i}. {insight}")
    
    lines.append(f"")
    lines.append(f"**风险提示**: 上述推断基于公开公告的逻辑推演，存在不确定性。建议结合：")
    lines.append(f"- 原始公告全文细节")
    lines.append(f"- 行业景气周期判断")
    lines.append(f"- 管理层访谈或投资者交流记录")
    lines.append(f"")

    return lines


def _section_annual_pdf(data):
    """年报PDF分析章节（支持annual_extract 20章节格式）"""
    lines = []
    lines.append("## 十五、年报PDF分析")
    lines.append("")
    
    if not data or data.get('error'):
        lines.append(f"**状态**: ❌ 获取失败")
        if data and data.get('error'):
            lines.append(f"- 错误: {data['error']}")
        lines.append("")
        return lines
    
    lines.append(f"**年报年份**: {data.get('year', '未知')}")
    lines.append(f"**标题**: {data.get('title', '未知')}")
    lines.append(f"**页数**: {data.get('page_count', 0)}页")
    pdf_path = data.get('pdf_path', '')
    if pdf_path:
        lines.append(f"**PDF路径**: `{pdf_path}`")
    lines.append("")
    
    # 目录
    toc = data.get('toc', [])
    if toc:
        lines.append("**主要章节**（前20项）:")
        for item in toc[:20]:
            indent = "  " * (item.get('level', 1) - 1)
            lines.append(f"{indent}- {item.get('title', '')} (p.{item.get('page', '')})")
        lines.append("")
    
    # 章节内容：优先 annual_extract 格式（20章节），fallback到旧格式（5章节）
    sections = data.get('sections', {})
    if sections and isinstance(sections, dict):
        # 检测是否为 annual_extract 格式（key为英文section key）
        ANNUAL_EXTRACT_KEYS = {
            'audit','dividend','top5_customers','top5_suppliers','actual_controller',
            'top10_shareholders','contingent','post_events','litigation','litigation_detail',
            'rd_spending','production_sales','capacity','subsidiaries','guarantee',
            'cip','goodwill','lt_equity','gov_subsidy','new_subsidiaries','auditor_change',
            'related_party',
        }
        is_new_format = any(k in ANNUAL_EXTRACT_KEYS for k in sections.keys())
        
        if is_new_format:
            lines.append("**📑 年报关键章节内容**（共{:d}章节）：\n".format(len(sections)))
            for key in sections:
                sdata = sections[key]
                name = sdata.get('name', key)
                desc = sdata.get('description', '')
                content = sdata.get('content', '')
                if not content or content.startswith('[未找到') or content.startswith('[无'):
                    continue
                lines.append(f"### {name}")
                if desc:
                    lines.append(f"_{desc}_  ")
                if len(content) > 3000:
                    lines.append(content[:3000] + "\n_...[内容截断]..._\n")
                else:
                    lines.append(content)
                lines.append("")
        else:
            # 旧格式（extract_key_sections 5章节）
            lines.append("**关键章节摘要**:")
            for key in ['management_discussion','risk_factors','financial_highlights','shareholders','important_matters']:
                if not sections.get(key):
                    continue
                label_map = {
                    'management_discussion': '管理层讨论与分析',
                    'risk_factors': '风险因素',
                    'financial_highlights': '财务数据摘要',
                    'shareholders': '股东情况',
                    'important_matters': '重要事项',
                }
                content = sections[key]
                if len(content) > 2000:
                    content = content[:2000] + "\n_...[截断]..._\n"
                lines.append(f"### {label_map.get(key, key)}")
                lines.append(f"```\n{content}\n```\n")
    
    return lines


def _section_peer_compare(data):
    lines = []
    lines.append("## 十一、同业财务对比")
    lines.append("")

    if not data or not data.get('has_data'):
        lines.append("_同业对比数据获取失败，请检查网络连接或股票代码。_")
        return lines

    # 直接嵌入 peer_compare 模块生成的 Markdown
    md = data.get('markdown', '')
    if md:
        # 去掉 peer_compare 自带的顶层标题（避免与报告章节重复）
        if md.startswith('## '):
            md = md.split('\n', 1)[1]
        lines.append(md)
    else:
        lines.append("_暂无对比数据_")

    return lines


def _section_rd_analysis(data):
    lines = []
    lines.append("## 十二、研发与利润归因分析")
    lines.append("")
    if not data or data.get('error'):
        lines.append("_研发与利润归因数据获取失败，请检查网络连接或股票代码。_")
        return lines

    # 调用 rd_analysis 模块的格式化函数（在同一目录，直接import）
    # rd_analysis 与 report.py 同在 scripts/ 下，用 from 相对导入
    from rd_analysis import format_rd_analysis
    formatted = format_rd_analysis(data)
    # 去掉 rd_mod 自己的顶层标题（避免重复）
    if formatted.startswith('## '):
        formatted = formatted.split('\n', 1)[1]
    lines.append(formatted)
    return lines


def _section_quote(data):
    """实时行情章节（支持批量多只股票）"""
    lines = []
    lines.append("## 十、实时行情")
    lines.append("")

    # 支持 dict（单只）或 list（批量）
    items = data if isinstance(data, list) else [data]
    if not items or (isinstance(data, dict) and not data):
        lines.append("*暂无行情数据*")
        lines.append("")
        return lines

    # 统计交易状态
    trading = sum(1 for it in items if it.get('status') in ('trading', 'success'))
    lines.append(f"**{len(items)}只股票** | {trading}只交易中\n")

    # 行情表格
    rows = []
    for it in items:
        code = it.get('code') or it.get('stock_code') or '?'
        name = it.get('name', '?')
        market_map = {'sh': '沪市', 'sz': '深市', 'hk': '港股', 'bse': '北交所', 'bj': '北交所', 'us': '美股', 'a': 'A股', 'A': 'A股'}
        market_label = market_map.get(it.get('market', ''), it.get('market', ''))
        price = it.get('current_price') or it.get('price') or '?'
        chg_raw = it.get('change') or it.get('chg') or '?'
        pct_raw = it.get('change_percent') or it.get('pct') or '?'
        try:
            chg_str = f'{float(chg_raw):+.2f}'
        except (ValueError, TypeError):
            chg_str = str(chg_raw) if chg_raw not in ('?', None, '') else '?'
        try:
            pct_str = f'{float(pct_raw):+.2f}%'
        except (ValueError, TypeError):
            pct_str = f'{pct_raw}%' if pct_raw and str(pct_raw) != '?' else '?'
        vol = it.get('volume') or it.get('vol_hands') or '?'
        time_str = it.get('time') or it.get('datetime') or ''
        status = it.get('status', '')
        emoji = {'trading': '✅', 'success': '✅', 'suspended': '💤', 'not_found': '❓'}.get(status, '❓')
        rows.append([emoji, code, name, market_label, price, chg_str, pct_str, vol, time_str])

    if rows:
        header = ['状态', '代码', '名称', '市场', '现价', '涨跌', '涨跌幅', '成交量', '时间']
        lines.append('| ' + ' | '.join(header) + ' |')
        lines.append('|' + '|'.join(['---'] * len(header)) + '|')
        for r in rows:
            lines.append('| ' + ' | '.join(str(v) for v in r) + ' |')
        lines.append("")

    # 非交易状态说明
    for it in items:
        status = it.get('status', '')
        if status in ('suspended', 'not_found', 'error'):
            code = it.get('code') or it.get('stock_code') or '?'
            name = it.get('name') or ''
            notes = {
                'suspended': f'{name}({code})停牌中',
                'not_found': f'{name}({code})未找到实时数据',
                'error': f'{name}({code})查询失败: {it.get("message", "")}'
            }
            lines.append(f"- {notes.get(status, status)}")
    if any(it.get('status') in ('suspended', 'not_found', 'error') for it in items):
        lines.append("")
    return lines


def _section_unknown(findings):
    lines = []
    lines.append("## 十六、信息缺失清单")
    lines.append(f"")
    lines.append("以下信息本次分析未能获取，建议手动补充:")
    lines.append(f"")
    lines.append("- [ ] 年报PDF全文（财务数据）")
    lines.append("- [ ] 重大仲裁/诉讼案的具体金额和进展")
    lines.append("- [ ] 高管辞职的真实原因")
    lines.append("- [ ] 子公司IPO辅导报告全文")
    lines.append("- [ ] 港股私有化要约的具体条款（收购价格、条件）")
    lines.append("- [ ] 问询函的详细内容")
    lines.append("- [ ] 独董核查意见全文")
    lines.append(f"")
    return lines


def _section_multi_year_trend(data):
    from scripts.multi_year_trend import format_markdown
    if not data:
        return ["\n## 17-multi-year-trend [DATA_MISSING]\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\n## 17-multi-year-trend\n\n", md]

def _section_earnings_forecast(data):
    from scripts.earnings_forecast import format_forecast_markdown
    if not data:
        return ["\n## 18-earnings-forecast [DATA_MISSING]\n"]
    md = format_forecast_markdown(data, data.get('_meta', {}).get('stock_code', ''))
    if md.startswith("## "):
        md = md[3:]
    return ["\n## 18-earnings-forecast\n\n", md]

def _section_valuation(data):
    from scripts.valuation import format_markdown
    if not data:
        return ["\n## 19-valuation [DATA_MISSING]\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\n## 19-valuation\n\n", md]

def _section_governance(data):
    from scripts.governance import format_markdown
    if not data:
        return ["\n## 20-governance [DATA_MISSING]\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\n## 20-governance\n\n", md]

def _section_share_history(data):
    from scripts.share_history import format_markdown
    if not data:
        return ["\n## 21-share-history [DATA_MISSING]\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\n## 21-share-history\n\n", md]

def _section_institutional(data):
    from scripts.institutional import format_markdown
    if not data:
        return ["\n## 22-institutional [DATA_MISSING]\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\n## 22-institutional\n\n", md]

def _section_investor_qa(data):
    from scripts.investor_qa import format_markdown
    if not data:
        return ["\n## 23-investor-qa [DATA_MISSING]\n"]
    md = format_markdown(data)
    if md.startswith("## "):
        md = md[3:]
    return ["\n## 23-investor-qa\n\n", md]


def _generate_timeline(findings, path):
    """生成事件时间线"""
    lines = ["# 重大事件时间线", ""]
    anns = findings.get('announcements', {}).get('recent_30', [])
    exec_changes = findings.get('executives', {}).get('changes', [])
    capital = findings.get('capital', {}).get('actions', [])
    related = findings.get('related', {}).get('deals', [])

    # 合并所有事件
    all_events = []
    for a in anns:
        all_events.append({'date': a.get('date', ''), 'title': a.get('title', ''), 'source': '公告'})
    for e in exec_changes:
        all_events.append({'date': e.get('date', ''), 'title': e.get('title', ''), 'source': '高管'})
    for c in capital:
        all_events.append({'date': c.get('date', ''), 'title': c.get('title', ''), 'source': '资金'})
    for r in related:
        all_events.append({'date': r.get('date', ''), 'title': r.get('title', ''), 'source': '资本运作'})

    # 去重+排序
    seen = set()
    unique = []
    for e in all_events:
        key = (e['date'], e['title'][:30])
        if key not in seen and e['date']:
            seen.add(key)
            unique.append(e)
    unique.sort(key=lambda x: x['date'], reverse=True)

    for e in unique[:50]:
        lines.append(f"- **{e['date']}** [{e['source']}] {e['title'][:80]}")

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def _generate_warnings(findings, path):
    """生成风险清单"""
    lines = ["# 风险信号清单", ""]

    # 财务风险
    fin_risks = findings.get('financial', {}).get('key_risks', [])
    if fin_risks:
        lines.append("## 财务风险")
        for r in fin_risks:
            lines.append(f"- ⚠️ {r}")
        lines.append("")

    # 高管风险
    exec_warnings = findings.get('executives', {}).get('summary', {}).get('warnings', [])
    if exec_warnings:
        lines.append("## 高管动态风险")
        for w in exec_warnings:
            lines.append(f"- {w}")
        lines.append("")

    # 资金风险
    cap_risks = findings.get('capital', {}).get('risks', [])
    if cap_risks:
        lines.append("## 资金动作风险")
        for r in cap_risks:
            lines.append(f"- ⚠️ {r.get('title','')}: {r.get('risk_signal','')}")
        lines.append("")

    # 监管风险
    regs = findings.get('regulatory', {}).get('records', [])
    if regs:
        severe = [r for r in regs if '🔴' in r.get('severity', '')]
        if severe:
            lines.append("## 监管风险")
            for r in severe:
                lines.append(f"- 🔴 {r.get('date','')} {r.get('title','')}")
            lines.append("")

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def _section_hkex_announcements(data):
    """港交所公告章节"""
    lines = []
    if not data or not isinstance(data, list) or len(data) == 0:
        lines.append("## 港交所公告")
        lines.append("")
        lines.append("未获取到港交所公告数据。")
        lines.append("")
        return lines
    
    lines.append("## 港交所公告")
    lines.append("")
    lines.append(f"共获取 **{len(data)}** 条港交所公告。")
    lines.append("")
    
    # 按类型分组
    type_groups = {}
    for ann in data:
        dt = ann.get('doc_type', '其他公告')
        if dt not in type_groups:
            type_groups[dt] = []
        type_groups[dt].append(ann)
    
    # 类型统计
    lines.append("### 公告类型分布")
    lines.append("")
    for dtype, anns in sorted(type_groups.items(), key=lambda x: -len(x[1])):
        lines.append(f"- **{dtype}**: {len(anns)}条")
    lines.append("")
    
    # 详细列表
    lines.append("### 公告明细")
    lines.append("")
    for i, ann in enumerate(data[:20]):
        title = ann.get('title', '')
        date = ann.get('date', '')
        dtype = ann.get('doc_type', '')
        pdf_url = ann.get('pdf_url', '')
        
        lines.append(f"{i+1}. **[{dtype}]** {date} — {title}")
        if pdf_url and not pdf_url.startswith('javascript:'):
            lines.append(f"   📎 [PDF]({pdf_url})")
    lines.append("")
    
    return lines


if __name__ == '__main__':
    # 简单测试
    os.makedirs('output/test_002180', exist_ok=True)
    report_path = generate_report({
        'stock': '002180',
        'market': 'a',
        'dims': ['announcements', 'financial', 'executives', 'capital', 'subsidiary', 'related', 'regulatory', 'structure', 'risk'],
        'date': '20260420',
        'findings': {}
    }, 'output/test_002180')
    print(f"Report: {report_path}")
