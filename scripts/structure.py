# -*- coding: utf-8 -*-
"""
模块8：股权结构分析
构建上市公司→子公司→关联方完整结构图
"""
import sys, json, requests, re
sys.stdout.reconfigure(encoding='utf-8')

def build_structure(stock_code, market, findings, data_dir=None):
    """
    基于公告数据和已知信息构建股权结构
    已知信息：通过公告标题推断子公司和关联方关系
    """
    result = {
        'stock_code': stock_code,
        'structure': {},
        'notes': [],
    }

    announcements = findings.get('announcements', {}).get('recent_30', [])
    related_deals = findings.get('related', {}).get('deals', [])
    subsidiary_ipo = findings.get('subsidiary', {}).get('subsidiaries', [])

    # 从公告推断结构
    # 1. 从"关于XXX的公告"标题推断关联方
    # 2. 从分拆上市公告推断子公司
    # 3. 从收购/出售公告推断资产关系

    structure = {
        'main_listed': {
            'name': stock_code,
            'type': '上市公司',
            'children': [],
            'related': [],
        }
    }

    # 子公司
    sub_names = set()
    for sub in subsidiary_ipo:
        name = sub.get('sub_company', '未知子公司')
        if name != '未知':
            sub_names.add(name)
        structure['main_listed']['children'].append({
            'name': name,
            'type': '拟分拆上市子公司',
            'detail': sub,
        })

    # 从资本运作推断关联方
    for deal in related_deals:
        title = deal.get('title', '')
        # 提取涉及的子公司/关联方名称
        # 模式："关于XXX的公告"、"关于收购/出售XXX的公告"
        m = re.search(r'关于(.{2,20}公司)的', title)
        if m:
            name = m.group(1)
            if name not in sub_names and stock_code not in name:
                structure['main_listed']['related'].append({
                    'name': name,
                    'deal': deal.get('type', ''),
                    'detail': deal.get('title', ''),
                })

    # 推断实际控制人
    ctrl = _find_actual_controller(findings)
    if ctrl:
        structure['actual_controller'] = ctrl

    result['structure'] = structure

    # 生成结构文本
    result['text'] = _render_structure_text(structure)

    return result


def _find_actual_controller(findings):
    """从公告识别实控人信息"""
    announcements = findings.get('announcements', {}).get('recent_30', [])
    for a in announcements:
        title = a.get('title', '')
        if '实际控制人' in title:
            return {
                'source': '公告',
                'announcement': title,
                'date': a.get('date', ''),
            }
    return None


def _render_structure_text(structure):
    """渲染结构文本图"""
    lines = []
    lines.append("股权结构图")
    lines.append("=" * 50)
    main = structure.get('main_listed', {})
    lines.append(f"【上市公司】{main.get('name', '')}")
    lines.append("│")
    lines.append("├─ 子公司/拟分拆资产")
    for child in main.get('children', []):
        lines.append(f"│   ├─ {child.get('name', '')} [{child.get('type', '')}]")
    lines.append("│")
    lines.append("└─ 关联方资本运作")
    for rel in main.get('related', [])[:10]:
        lines.append(f"    ├─ {rel.get('name', '')} [{rel.get('deal', '')}]")
    ctrl = structure.get('actual_controller')
    if ctrl:
        lines.append("│")
        lines.append(f"【实控人】{ctrl.get('source', '')}")
    return '\n'.join(lines)


if __name__ == '__main__':
    result = build_structure('002180', 'a', {})
    print(result['text'])
