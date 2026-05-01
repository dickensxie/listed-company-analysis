# -*- coding: utf-8 -*-
"""
模块3：高管的动态分析
辞职/新任/薪酬方案/股权激励调整
"""
import sys, json, requests, re, time
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

def fetch_executives(stock_code, market='a', data_dir=None):
    """从公告列表中识别高管变动"""
    result = {
        'stock_code': stock_code,
        'changes': [],
        'equity_incentives': [],
        'summary': {},
    }

    # 从东方财富公告中识别高管变动
    url = (f"https://np-anotice-stock.eastmoney.com/api/security/ann"
           f"?cb=&sr=-1&page_size=200&page_index=1&ann_type=A"
           f"&client_source=web&f_node=0&s_node=0&stock_list={stock_code}")
    try:
        r = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://data.eastmoney.com/'
        }, timeout=20)
        r.encoding = 'utf-8'
        data = r.json()
        items = data.get('data', {}).get('list', [])
    except:
        items = []

    changes = []
    incentives = []

    # 高管变动关键词
    exec_keywords = ['董事长', '副董事长', '总裁', '总经理', '副总经理',
                      '董事', '监事', '独立董事', '财务总监', '董事会秘书',
                      '辞职', '离任', '新任', '选举', '聘用', '任命',
                      '副总裁', '首席', 'COO', 'CFO', '董秘']

    # 股权激励关键词
    incentive_keywords = ['股权激励', '限制性股票', '股票期权', '员工持股',
                          '行权', '授予', '注销', '回购', '行权价格',
                          '解锁', '归属', 'ESOP']

    for item in items:
        title = item.get('title', '') or item.get('title_ch', '')
        notice_date = item.get('notice_date', '')[:10]
        columns = [c.get('column_name', '') for c in item.get('columns', [])]
        col_str = '|'.join(columns)

        # 高管变动
        is_exec = any(k in title for k in exec_keywords)
        is_incentive = any(k in title for k in incentive_keywords)
        is_egm = '临时股东会' in title or '股东大会' in title

        if is_exec or ('股东大会' in col_str and is_egm):
            changes.append({
                'date': notice_date,
                'title': title,
                'categories': col_str,
                'art_code': item.get('art_code', ''),
                'type': _classify_exec_change(title),
            })

        if is_incentive:
            incentives.append({
                'date': notice_date,
                'title': title,
                'art_code': item.get('art_code', ''),
                'type': _classify_incentive(title),
            })

    # 汇总
    result['changes'] = changes
    result['equity_incentives'] = incentives
    result['change_count'] = len(changes)
    result['summary'] = _summarize_exec(changes, incentives)

    return result


def _classify_exec_change(title):
    """分类高管变动类型"""
    if '辞职' in title or '离任' in title:
        return '辞职/离职'
    elif '新任' in title or '选举' in title:
        return '新任/补选'
    elif '变更' in title:
        return '变更'
    elif '选举' in title:
        return '换届选举'
    else:
        return '其他'


def _classify_incentive(title):
    """分类股权激励类型"""
    if '注销' in title:
        return '注销/取消'
    elif '回购' in title:
        return '回购'
    elif '授予' in title:
        return '授予'
    elif '行权' in title:
        return '行权'
    elif '激励计划' in title:
        return '新计划'
    else:
        return '其他'


def _summarize_exec(changes, incentives):
    """高管动态摘要"""
    summary = {
        'total_changes': len(changes),
        'resignations': [c for c in changes if c['type'] == '辞职/离职'],
        'new_appointments': [c for c in changes if c['type'] in ('新任/补选', '变更')],
        'total_incentives': len(incentives),
        'incentive_cancellations': [i for i in incentives if i['type'] == '注销/取消'],
        'latest_change': changes[0] if changes else None,
    }

    # 危险信号识别
    warnings = []
    if any('董事长' in c['title'] and '辞职' in c['title'] for c in changes):
        warnings.append("⚠️ 董事长辞职（需关注原因）")
    if any('总裁' in c['title'] and '辞职' in c['title'] for c in changes):
        warnings.append("⚠️ 总裁辞职（需关注原因）")
    if any(i['type'] == '注销/取消' for i in incentives):
        warnings.append("⚠️ 股权激励注销（可能损害员工积极性）")
    if summary['total_changes'] >= 5:
        warnings.append("⚠️ 高管变动频繁")

    summary['warnings'] = warnings
    return summary


if __name__ == '__main__':
    result = fetch_executives('002180')
    print(f"高管变动: {result['change_count']}条")
    print(f"股权激励: {result['summary']['total_incentives']}条")
    for c in result['changes'][:5]:
        print(f"  {c['date']} [{c['type']}] {c['title'][:60]}")
