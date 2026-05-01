# -*- coding: utf-8 -*-
"""
投资逻辑自动生成模块

基于上市公司全景分析结果，自动生成结构化投资逻辑框架
输出格式：核心投资逻辑 + 关键假设 + 风险提示
"""
import json, os
from datetime import datetime


def generate_investment_thesis(analysis_data, stock_code, market='a'):
    """
    生成投资逻辑

    参数:
        analysis_data: analyze.py 的 results.json 内容
        stock_code: 股票代码
        market: 市场

    返回:
        {
            "thesis": "核心投资逻辑（3-5句话）",
            "catalysts": ["催化剂1", "催化剂2"],
            "assumptions": ["关键假设1", "关键假设2"],
            "risks": ["风险1", "风险2"],
            "investment_rating": "买入/增持/中性/减持",
            "target_price": None,  # 需要估值模型支持
            "markdown": "完整Markdown文本",
        }
    """
    findings = analysis_data.get('findings', {})
    result = {
        "thesis": "",
        "catalysts": [],
        "assumptions": [],
        "risks": [],
        "investment_rating": "中性",
        "target_price": None,
        "markdown": "",
    }

    # ─────────────────────────────────────────────
    # 1. 核心投资逻辑提取
    # ─────────────────────────────────────────────
    thesis_parts = []
    company_name = findings.get('quote', {}).get('name', stock_code)

    # 1.1 行业地位
    industry = findings.get('industry', {})
    if industry.get('competitors'):
        comp_count = len(industry['competitors'])
        thesis_parts.append(f"申万行业可比公司{comp_count}家")

    # 1.2 财务亮点
    financial = findings.get('financial', {})
    multi_year = findings.get('multi_year_trend', {})
    quote = findings.get('quote', {})

    fin_highlights = []
    
    # 从 financial 提取
    if financial.get('revenue'):
        rev = financial['revenue']
        if rev > 100:
            fin_highlights.append(f"营收{rev:.0f}亿")
    if financial.get('net_profit'):
        np = financial['net_profit']
        if np > 0:
            fin_highlights.append(f"净利{np:.1f}亿")
        elif np < 0:
            fin_highlights.append(f"净亏损{abs(np):.1f}亿")
    if financial.get('gross_margin'):
        gm = financial['gross_margin']
        if gm > 50:
            fin_highlights.append(f"高毛利率{gm:.0f}%")
        elif gm > 30:
            fin_highlights.append(f"毛利率{gm:.0f}%")
    if financial.get('roe'):
        roe = financial['roe']
        if roe > 15:
            fin_highlights.append(f"ROE {roe:.0f}%")
    
    # 从 multi_year_trend 提取
    if multi_year.get('revenue_cagr'):
        cagr = multi_year['revenue_cagr']
        if cagr > 20:
            fin_highlights.append(f"营收CAGR {cagr:.0f}%")
        elif cagr > 10:
            fin_highlights.append(f"营收稳健增长{cagr:.0f}%")
    if multi_year.get('profit_cagr'):
        cagr = multi_year['profit_cagr']
        if cagr > 20:
            fin_highlights.append(f"净利CAGR {cagr:.0f}%")
    if multi_year.get('trend') == 'up':
        fin_highlights.append("财务趋势向好")
    elif multi_year.get('trend') == 'down':
        fin_highlights.append("财务趋势下行")

    if fin_highlights:
        thesis_parts.append("、".join(fin_highlights))

    # 1.3 估值优势
    valuation = findings.get('valuation', {})
    val_highlights = []
    if valuation.get('pe_ttm') and isinstance(valuation['pe_ttm'], (int, float)):
        pe = valuation['pe_ttm']
        if pe > 0 and pe < 15:
            val_highlights.append(f"低估值PE{pe:.0f}x")
        elif pe > 0 and pe < 25:
            val_highlights.append(f"PE{pe:.0f}x")
    if valuation.get('pb') and isinstance(valuation['pb'], (int, float)):
        pb = valuation['pb']
        if pb > 0 and pb < 2:
            val_highlights.append(f"PB{pb:.1f}x")
    if valuation.get('total_mv'):
        mv = valuation['total_mv']
        if mv > 500:
            val_highlights.append(f"市值{mv:.0f}亿")

    if val_highlights:
        thesis_parts.append("、".join(val_highlights))

    # 1.4 业务亮点
    industry_data = findings.get('industry', {})
    if industry_data.get('main_business'):
        biz = industry_data['main_business'][:50]
        thesis_parts.append(f"主营{biz}")
    
    # 1.5 同业对比亮点
    peer = findings.get('peer_compare', {})
    if peer.get('conclusion'):
        thesis_parts.append(f"同行对比：{peer['conclusion'][:30]}")

    result["thesis"] = f"{company_name}：{'；'.join(thesis_parts)}。"

    # ─────────────────────────────────────────────
    # 2. 催化剂识别
    # ─────────────────────────────────────────────
    catalysts = []

    # 2.1 子公司IPO
    subsidiary = findings.get('subsidiary_ipo', {})
    if subsidiary.get('subsidiaries'):
        for sub in subsidiary['subsidiaries']:
            if sub.get('stage') in ['辅导备案', '辅导验收', '已申报']:
                catalysts.append(f"子公司{sub.get('name', '')}IPO进展（{sub.get('stage')}）")

    # 2.2 重大公告
    announcements = findings.get('announcements', {})
    if announcements.get('key_events'):
        for evt in announcements['key_events'][:3]:
            title = evt.get('title', '')[:30]
            if '收购' in title or '重组' in title or '投资' in title:
                catalysts.append(title)

    # 2.3 产能扩张
    annual_pdf = findings.get('annual_pdf', {})
    if annual_pdf.get('sections', {}).get('capacity'):
        cap_text = annual_pdf['sections']['capacity'].get('content', '')
        if '扩产' in cap_text or '新增产能' in cap_text:
            catalysts.append("产能扩张中")

    # 2.4 分红
    if findings.get('dividend'):
        catalysts.append("稳定分红")

    result["catalysts"] = catalysts[:5]

    # ─────────────────────────────────────────────
    # 3. 关键假设
    # ─────────────────────────────────────────────
    assumptions = []

    if multi_year.get('revenue_cagr'):
        assumptions.append(f"营收延续{multi_year['revenue_cagr']:.0f}%增速")

    if financial.get('gross_margin'):
        assumptions.append(f"毛利率维持{financial['gross_margin']:.0f}%水平")

    assumptions.append("行业景气度保持稳定")
    assumptions.append("无重大政策变化")

    result["assumptions"] = assumptions[:4]

    # ─────────────────────────────────────────────
    # 4. 风险提示
    # ─────────────────────────────────────────────
    risks = []

    # 4.1 从风险评分提取
    risk_score = findings.get('risk_score', {})
    if risk_score.get('risks'):
        for r in risk_score['risks'][:5]:
            signal = r.get('signal', '')
            if signal:
                risks.append(signal)

    # 4.2 从公告提取
    if announcements.get('key_events'):
        for evt in announcements['key_events']:
            title = evt.get('title', '')
            if '诉讼' in title or '处罚' in title or '调查' in title:
                risks.append(title[:30])

    # 4.3 从监管历史提取
    regulatory = findings.get('regulatory', {})
    if regulatory.get('events'):
        for evt in regulatory['events'][:3]:
            evt_type = evt.get('type', '')
            if '处罚' in evt_type or '问询' in evt_type:
                risks.append(f"监管{evt_type}")

    # 4.4 财务风险
    if financial.get('audit_opinion'):
        audit = financial['audit_opinion']
        if '保留' in audit or '无法' in audit:
            risks.append(f"审计意见：{audit}")
    if financial.get('net_profit') and financial['net_profit'] < 0:
        risks.append("净利润亏损")

    if risks:
        result["risks"] = list(set(risks))[:6]
    else:
        result["risks"] = ["行业竞争加剧", "宏观经济下行"]

    # ─────────────────────────────────────────────
    # 5. 投资评级（简化版，基于风险评分）
    # ─────────────────────────────────────────────
    if risk_score.get('score') is not None:
        score = risk_score['score']
        if score < 30:
            result["investment_rating"] = "增持"
        elif score < 50:
            result["investment_rating"] = "中性"
        elif score < 70:
            result["investment_rating"] = "减持"
        else:
            result["investment_rating"] = "规避"

    # ─────────────────────────────────────────────
    # 6. 生成Markdown
    # ─────────────────────────────────────────────
    md_lines = []
    md_lines.append("## 投资逻辑")
    md_lines.append("")
    md_lines.append(f"**核心观点**: {result['thesis']}")
    md_lines.append("")

    if result['catalysts']:
        md_lines.append("**催化剂**:")
        for c in result['catalysts']:
            md_lines.append(f"- {c}")
        md_lines.append("")

    if result['assumptions']:
        md_lines.append("**关键假设**:")
        for a in result['assumptions']:
            md_lines.append(f"- {a}")
        md_lines.append("")

    if result['risks']:
        md_lines.append("**风险提示**:")
        for r in result['risks']:
            md_lines.append(f"- {r}")
        md_lines.append("")

    md_lines.append(f"**投资评级**: {result['investment_rating']}")
    md_lines.append("")
    md_lines.append("> ⚠️ 以上投资逻辑由AI自动生成，仅供参考，不构成投资建议。")

    result["markdown"] = "\n".join(md_lines)

    return result


def save_investment_thesis(thesis_data, output_dir, stock_code):
    """保存投资逻辑到文件"""
    os.makedirs(output_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(output_dir, 'investment_thesis.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(thesis_data, f, ensure_ascii=False, indent=2)

    # Markdown
    md_path = os.path.join(output_dir, 'investment_thesis.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(thesis_data['markdown'])

    return json_path, md_path


if __name__ == '__main__':
    import sys
    stock = sys.argv[1] if len(sys.argv) > 1 else '002180'

    # 读取分析结果
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    results_path = os.path.join(parent_dir, 'output', f'{stock}_*', 'data', 'results.json')

    import glob
    matches = glob.glob(results_path)
    if not matches:
        print(f"未找到 {stock} 的分析结果，请先运行 analyze.py")
        sys.exit(1)

    latest = sorted(matches)[-1]
    print(f"读取: {latest}")

    with open(latest, encoding='utf-8') as f:
        data = json.load(f)

    thesis = generate_investment_thesis(data, stock)
    print(thesis['markdown'])
    print(f"\n投资评级: {thesis['investment_rating']}")
