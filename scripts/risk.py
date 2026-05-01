# -*- coding: utf-8 -*-
"""
模块9：综合风险评级
基于各维度发现进行综合风险评分
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

RISK_WEIGHTS = {
    'audit': 20,      # 审计意见
    'lawsuit': 15,    # 重大诉讼
    'executive': 10,  # 高管变动
    'capital': 10,   # 资金动作
    'regulatory': 15, # 监管记录
    'financial': 15,  # 财务风险
    'subsidiary': 15,  # 子公司IPO障碍
}

def assess_risk(findings):
    """
    综合所有维度进行风险评级
    返回：{score, level, signals, summary}
    """
    score = 0
    signals = []

    # 1. 审计意见风险
    audit = findings.get('financial', {}).get('audit_opinion') or '未知'
    if '非标准' in audit or '保留' in audit or '无法表示' in audit:
        score += RISK_WEIGHTS['audit']
        signals.append({'dim': '审计意见', 'level': '🔴 高',
                         'detail': f'审计意见：{audit}'})
    elif '强调事项' in audit:
        score += RISK_WEIGHTS['audit'] // 2
        signals.append({'dim': '审计意见', 'level': '🟡 中',
                         'detail': f'带强调事项段：{audit}'})

    # 2. 重大诉讼风险
    anns = findings.get('announcements', {}).get('key_events', [])
    lawsuits = [a for a in anns if '诉讼' in a.get('title', '') or '仲裁' in a.get('title', '')]
    if lawsuits:
        score += RISK_WEIGHTS['lawsuit']
        signals.append({'dim': '重大诉讼', 'level': '🔴 高',
                         'detail': f'存在{len(lawsuits)}项重大诉讼/仲裁公告'})

    # 3. 高管变动风险
    exec_sum = findings.get('executives', {}).get('summary', {})
    if exec_sum.get('warnings'):
        for w in exec_sum['warnings']:
            if '⚠️ 董事长' in w or '⚠️ 总裁' in w:
                score += RISK_WEIGHTS['executive']
                signals.append({'dim': '高管动态', 'level': '🔴 高', 'detail': w})
            else:
                score += RISK_WEIGHTS['executive'] // 2
                signals.append({'dim': '高管动态', 'level': '🟡 中', 'detail': w})

    # 4. 资金动作风险
    cap_risks = findings.get('capital', {}).get('risks', [])
    if cap_risks:
        score += min(RISK_WEIGHTS['capital'], len(cap_risks) * 5)
        for r in cap_risks[:3]:
            signals.append({'dim': '资金动作', 'level': '🟡 中', 'detail': r.get('risk_signal', '')})

    # 5. 监管历史风险
    reg_sum = findings.get('regulatory', {}).get('summary', {})
    by_sev = reg_sum.get('by_severity', {})
    if '🔴 严重' in by_sev:
        score += RISK_WEIGHTS['regulatory']
        signals.append({'dim': '监管记录', 'level': '🔴 高',
                         'detail': f'存在{by_sev.get("🔴 严重",0)}项严重监管记录'})
    elif '🟡 中等' in by_sev:
        score += RISK_WEIGHTS['regulatory'] // 2
        signals.append({'dim': '监管记录', 'level': '🟡 中',
                         'detail': f'存在{by_sev.get("🟡 中等",0)}项监管关注'})

    # 6. 财务风险
    fin_risks = findings.get('financial', {}).get('key_risks', [])
    if fin_risks:
        score += min(RISK_WEIGHTS['financial'], len(fin_risks) * 5)
        for r in fin_risks[:3]:
            signals.append({'dim': '财务风险', 'level': '🟡 中', 'detail': r})

    # 7. 子公司IPO障碍
    sub = findings.get('subsidiary', {})
    subs = sub.get('subsidiaries', [])
    if subs:
        # 辅导期超2年=高风险
        latest_date = subs[0].get('date', '2020-01-01') if subs else '2020-01-01'
        year_diff = 2026 - int(latest_date[:4]) if latest_date.startswith('20') else 0
        if year_diff >= 2:
            score += RISK_WEIGHTS['subsidiary']
            signals.append({'dim': '子公司IPO', 'level': '🔴 高',
                             'detail': f'辅导期超{year_diff}年仍未申报，存在实质性障碍'})
        else:
            score += RISK_WEIGHTS['subsidiary'] // 2
            signals.append({'dim': '子公司IPO', 'level': '🟡 中',
                             'detail': f'正在筹划{len(subs)}项分拆/上市'})

    # 8. 关联方资本运作风险
    rel_risks = findings.get('related', {}).get('risks', [])
    if rel_risks:
        score += min(10, len(rel_risks) * 3)
        for r in rel_risks[:2]:
            signals.append({'dim': '关联方运作', 'level': '🟡 中', 'detail': r.get('risk', '')})

    # 等级
    if score >= 60:
        level = '🔴 高风险'
    elif score >= 30:
        level = '🟡 中风险'
    else:
        level = '🟢 低风险'

    return {
        'score': min(score, 100),
        'level': level,
        'signals': signals,
        'summary': {
            'high_risk': [s for s in signals if s['level'] == '🔴 高'],
            'medium_risk': [s for s in signals if s['level'] == '🟡 中'],
        }
    }


if __name__ == '__main__':
    from scripts.announcements import fetch_announcements
    from scripts.executives import fetch_executives
    from scripts.capital import fetch_capital_actions
    from scripts.subsidiary import fetch_subsidiary_ipo
    from scripts.financials import fetch_financials
    from scripts.related_deals import fetch_related_deals
    from scripts.regulatory import fetch_regulatory_history

    findings = {
        'announcements': fetch_announcements('002180'),
        'executives': fetch_executives('002180'),
        'capital': fetch_capital_actions('002180'),
        'subsidiary': fetch_subsidiary_ipo('002180'),
        'financial': fetch_financials('002180'),
        'related': fetch_related_deals('002180'),
        'regulatory': fetch_regulatory_history('002180'),
    }
    result = assess_risk(findings)
    print(f"风险评分: {result['score']}/100 | {result['level']}")
    for s in result['signals']:
        print(f"  {s['level']} [{s['dim']}] {s['detail']}")
