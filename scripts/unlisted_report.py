# -*- coding: utf-8 -*-
"""
未上市公司分析报告生成
"""
import sys, os, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def _sec(num, title, lines):
    """生成带编号的章节"""
    return [f"## {num}、{title}", ""] + lines + [""]


def _table(headers, rows):
    """生成Markdown表格"""
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return lines


def generate_unlisted_report(results, out_dir, company_name):
    """生成未上市公司分析Markdown报告"""
    findings = results.get('findings', {})
    date = results.get('date', datetime.now().strftime('%Y-%m-%d'))

    lines = []
    lines.append(f"# {company_name} — 未上市公司全景分析报告")
    lines.append(f"**分析日期**: {date}")
    lines.append(f"**报告模式**: 未上市公司（工商+融资+法律+舆情+IPO）")
    lines.append("")

    # ── 一、基本工商信息 ──────────────────────────────
    basic = findings.get('unlisted_basic', {})
    basic_lines = []
    if basic.get('name'):
        basic_lines += [f"- **公司名称**: {basic['name']}"]
    if basic.get('unified_credit_code'):
        basic_lines += [f"- **统一社会信用代码**: {basic['unified_credit_code']}"]
    if basic.get('registered_capital'):
        basic_lines += [f"- **注册资本**: {basic['registered_capital']}"]
    if basic.get('legal_representative'):
        basic_lines += [f"- **法定代表人**: {basic['legal_representative']}"]
    if basic.get('established'):
        basic_lines += [f"- **成立日期**: {basic['established']}"]
    if basic.get('status'):
        basic_lines += [f"- **经营状态**: {basic['status']}"]
    if basic.get('business_scope'):
        scope = basic['business_scope']
        if len(scope) > 300:
            scope = scope[:300] + '...'
        basic_lines += [f"- **经营范围**: {scope}"]
    if basic.get('source'):
        basic_lines += [f"**数据来源**: {basic['source']}"]
    if not basic_lines:
        basic_lines = ["*工商信息获取失败，请检查公司名称是否准确*"]
    if basic.get('error'):
        basic_lines += [f"*⚠️ 错误: {basic['error']}*"]
    lines += _sec(1, '基本工商信息', basic_lines)

    # ── 二、股权结构 ─────────────────────────────────
    equity = findings.get('unlisted_equity', {})
    equity_lines = []
    if equity.get('count', 0) > 0:
        equity_lines += [f"**股东数量**: {equity['count']}"]
        equity_lines += [""]
        headers = ['股东名称', '持股比例']
        rows = []
        for s in equity.get('shareholders', [])[:15]:
            pct = s.get('share_pct', '未知')
            rows.append([s.get('name', '未知'), pct])
        if rows:
            equity_lines += _table(headers, rows)
    else:
        equity_lines = ["*股东信息获取失败（可能需要登录天眼查）*"]
    if equity.get('error'):
        equity_lines += [f"*⚠️ 错误: {equity['error']}*"]
    lines += _sec(2, '股权结构（股东穿透）', equity_lines)

    # ── 三、融资历史 ─────────────────────────────────
    financing = findings.get('unlisted_financing', {})
    fin_lines = []
    if financing.get('count', 0) > 0:
        fin_lines += [f"**融资记录**: {financing['count']}条"]
        fin_lines += [""]
        headers = ['时间', '轮次', '金额', '来源']
        rows = []
        for r in financing.get('rounds', []):
            rows.append([
                r.get('date', ''),
                r.get('round', ''),
                r.get('amount', ''),
                r.get('source', ''),
            ])
        if rows:
            fin_lines += _table(headers, rows)
    else:
        fin_lines = ["*暂无公开融资记录（未融资/数据未公开）*"]
    if financing.get('xiniu_error') or financing.get('tyc_error'):
        fin_lines += [f"*⚠️ 部分数据源不可用*"]
    lines += _sec(3, '融资历史', fin_lines)

    # ── 四、法律风险 ─────────────────────────────────
    legal = findings.get('unlisted_legal', {})
    legal_lines = []
    risk_lvl = legal.get('legal_risk_level', '未知')
    risk_emoji = {'低': '🟢', '中低': '🟡', '中高': '🟠', '高': '🔴'}.get(risk_lvl, '⚪')
    legal_lines += [f"**法律风险等级**: {risk_emoji} {risk_lvl}"]
    legal_lines += [""]
    legal_lines += [f"- 被执行人记录: {legal.get('execution_count', 0)} 条"]
    legal_lines += [f"- 裁判文书: {legal.get('judgment_count', 0)} 条"]
    legal_lines += [f"- 行政处罚: {len(legal.get('admin_penalties', []))} 条"]
    legal_lines += [""]

    if legal.get('execution_records'):
        legal_lines += ["**被执行人详情**"]
        headers = ['案号', '金额', '执行法院', '日期']
        rows = [[r.get('case_no', ''), r.get('amount', ''), r.get('court', ''), r.get('date', '')]
                for r in legal.get('execution_records', [])[:10]]
        if rows:
            legal_lines += _table(headers, rows)
        legal_lines += [""]

    if legal.get('judgment_records'):
        legal_lines += ["**裁判文书摘要**"]
        headers = ['案号', '案由', '金额']
        rows = [[r.get('case_no', ''), r.get('reason', ''), r.get('amount', '')]
                for r in legal.get('judgment_records', [])[:10]]
        if rows:
            legal_lines += _table(headers, rows)
        legal_lines += [""]

    if legal.get('risk_tags'):
        legal_lines += [f"**信用风险标签**: {' / '.join(legal['risk_tags'])}"]
    lines += _sec(4, '法律风险（被执行/诉讼/处罚）', legal_lines)

    # ── 五、新闻舆情 ─────────────────────────────────
    news = findings.get('unlisted_news', {})
    news_lines = []
    sentiment = news.get('sentiment', '未知')
    sentiment_emoji = {'偏正面': '📈', '略偏正面': '📊', '中性': '➖', '略偏负面': '📉', '偏负面': '🔴'}.get(sentiment, '❓')
    news_lines += [f"**舆情倾向**: {sentiment_emoji} {sentiment}（正面{news.get('pos_count', 0)}条 / 负面{news.get('neg_count', 0)}条）"]
    news_lines += [""]
    news_lines += [f"**新闻数量**: {news.get('count', 0)}条"]
    news_lines += [""]
    if news.get('news'):
        headers = ['日期', '标题', '来源', '倾向']
        rows = [[n.get('date', ''), n.get('title', '')[:40], n.get('source', ''), n.get('sentiment', '')]
                for n in news.get('news', [])[:15]]
        if rows:
            news_lines += _table(headers, rows)
    else:
        news_lines += ["*暂无公开新闻*"]
    if news.get('iwencai_error'):
        news_lines += [f"*⚠️ 同花顺问财不可用*"]
    lines += _sec(5, '新闻舆情', news_lines)

    # ── 六、IPO辅导状态 ──────────────────────────────
    ipo_data = findings.get('unlisted_ipo', {})
    ipo_lines = []
    if ipo_data.get('has_coaching'):
        ipo_lines += [f"**状态**: 📋 正在/已完成IPO辅导"]
        ipo_lines += [""]
        headers = ['公司', '股票代码', '板块', '辅导机构', '监管局', '状态', '报告期数']
        rows = []
        for rec in ipo_data.get('coaching_records', []):
            rows.append([
                rec.get('company', ''),
                rec.get('stock_code', ''),
                rec.get('plate', ''),
                rec.get('coaching_institution', ''),
                rec.get('regulator', ''),
                rec.get('status', ''),
                rec.get('report_count', 0),
            ])
        if rows:
            ipo_lines += _table(headers, rows)
    else:
        ipo_lines += ["*未查询到IPO辅导备案记录（可能未启动IPO，或尚未在CSRC公示）*"]
    if ipo_data.get('csrc_status') and ipo_data.get('csrc_status') not in ['found', 'not_found']:
        ipo_lines += [f"*CSRC查询状态: {ipo_data['csrc_status']}*"]
    lines += _sec(6, 'IPO辅导状态', ipo_lines)

    # ── 七、股权激励/ESOP ────────────────────────────
    esop = findings.get('unlisted_esop', {})
    esop_lines = []
    if esop.get('has_esop') or esop.get('count', 0) > 0:
        esop_lines += [f"**股权激励记录**: {esop['count']}条"]
        if esop.get('holding_platforms'):
            esop_lines += [f"**员工持股平台**: {'; '.join(esop['holding_platforms'])}"]
        esop_lines += [""]
        headers = ['日期', '变动类型', '变动比例', '金额', '来源']
        rows = [[r.get('date', ''), r.get('type', ''), r.get('change_pct', ''), r.get('amount', ''), r.get('source', '')]
                for r in esop.get('esop_records', [])[:15]]
        if rows:
            esop_lines += _table(headers, rows)
    else:
        esop_lines += ["*未查询到公开股权激励记录*"]
    lines += _sec(7, '股权激励（ESOP）', esop_lines)

    # ── 综合结论 ──────────────────────────────────────
    lines += ["---", ""]
    lines += ["## 综合结论", ""]

    risk_items = []
    good_items = []

    # 工商状态
    basic = findings.get('unlisted_basic', {})
    if basic.get('status') in ['存续', '在业', '营业']:
        good_items.append("✅ 经营状态正常")
    elif basic.get('status') in ['注销', '吊销', '停业']:
        risk_items.append(f"⚠️ 经营状态异常: {basic.get('status')}")

    # 法律风险
    legal = findings.get('unlisted_legal', {})
    if legal.get('execution_count', 0) > 0:
        risk_items.append(f"⚠️ 存在{legal['execution_count']}条被执行人记录")
    if legal.get('judgment_count', 0) > 5:
        risk_items.append(f"⚠️ 存在{legal['judgment_count']}条裁判文书")

    # IPO状态
    ipo_data = findings.get('unlisted_ipo', {})
    if ipo_data.get('has_coaching'):
        good_items.append("📋 已在CSRC进行IPO辅导备案")
    else:
        risk_items.append("⚠️ 未查询到IPO辅导备案")

    # 融资
    financing = findings.get('unlisted_financing', {})
    if financing.get('count', 0) > 0:
        total_rounds = financing['count']
        good_items.append(f"💰 已有{total_rounds}轮融资记录")
    else:
        risk_items.append("⚠️ 无公开融资记录")

    # 舆情
    news = findings.get('unlisted_news', {})
    if news.get('neg_count', 0) > news.get('pos_count', 0) * 2:
        risk_items.append(f"🔴 舆情偏负面（正面{news.get('pos_count',0)} / 负面{news.get('neg_count',0)}）")

    if risk_items:
        lines += ["**风险提示**"]
        for item in risk_items:
            lines += [f"- {item}"]
        lines += [""]

    if good_items:
        lines += ["**正面信息**"]
        for item in good_items:
            lines += [f"- {item}"]
        lines += [""]

    if not risk_items and not good_items:
        lines += ["*数据有限，建议通过线下尽调进一步核实*"]

    lines += [""]
    lines += ["---", ""]
    lines += [f"*本报告数据来源于公开信息（天眼查/CSRC/中国执行信息公开网/新闻），"]
    lines += [f"*仅供参考，不构成投资建议。*"]
    lines += [f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"]

    # 写入文件
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, 'report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return report_path
