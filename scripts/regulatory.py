# -*- coding: utf-8 -*-
"""
模块7：监管历史追溯
问询函/处罚/核查意见/监管措施
"""
import sys, json, requests, re, time
sys.stdout.reconfigure(encoding='utf-8')

def fetch_regulatory_history(stock_code, market='a', data_dir=None):
    """追溯监管历史"""
    result = {'stock_code': stock_code, 'records': [], 'count': 0, 'summary': {}}

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

    reg_keywords = [
        '问询函', '监管函', '关注函', '核查意见',
        '警示函', '行政处罚', '立案', '整改',
        '自律监管', '公开谴责', '通报批评',
        '非标准审计报告', '审计问题', '保留意见',
        '强调事项', '持续经营', '内部控制',
    ]

    records = []
    for item in items:
        title = item.get('title', '') or item.get('title_ch', '')
        notice_date = item.get('notice_date', '')[:10]
        art_code = item.get('art_code', '')
        columns = [c.get('column_name', '') for c in item.get('columns', [])]
        col_str = '|'.join(columns)

        is_reg = any(k in title for k in reg_keywords)
        is_reg_cat = any(c in col_str for c in ['监管', '核查', '问询', '核查意见'])

        if is_reg or is_reg_cat:
            records.append({
                'date': notice_date,
                'title': title,
                'art_code': art_code,
                'category': col_str,
                'severity': _assess_severity(title, col_str),
                'type': _classify_reg(title, col_str),
            })

    result['records'] = records
    result['count'] = len(records)
    result['summary'] = _summarize_reg(records)

    return result


def _classify_reg(title, category):
    """分类监管类型"""
    if '问询函' in title or '问询' in category:
        return '问询函'
    elif '关注函' in title:
        return '关注函'
    elif '核查意见' in title or '核查意见' in category:
        return '保荐机构核查意见'
    elif '行政处罚' in title:
        return '行政处罚'
    elif '警示' in title:
        return '警示函'
    elif '立案' in title:
        return '立案调查'
    elif '公开谴责' in title:
        return '公开谴责'
    elif '非标准' in title or '非标' in title:
        return '非标准审计意见'
    elif '强调事项' in title:
        return '强调事项'
    else:
        return '其他监管事项'


def _assess_severity(title, category):
    """评估监管事项严重程度"""
    if any(k in title for k in ['行政处罚', '立案', '公开谴责']):
        return '🔴 严重'
    elif any(k in title for k in ['问询函']):
        return '🟡 中等'
    elif any(k in title for k in ['关注函', '警示', '核查意见']):
        return '🟡 中等'
    elif any(k in title for k in ['非标准', '保留意见', '强调事项', '持续经营']):
        return '🔴 财务风险'
    else:
        return '🟢 轻微'


def _summarize_reg(records):
    summary = {
        'total': len(records),
        'by_severity': {},
        'by_type': {},
        'latest': records[0] if records else None,
    }
    for r in records:
        summary['by_severity'][r['severity']] = \
            summary['by_severity'].get(r['severity'], 0) + 1
        summary['by_type'][r['type']] = \
            summary['by_type'].get(r['type'], 0) + 1
    return summary


if __name__ == '__main__':
    result = fetch_regulatory_history('002180')
    print(f"监管记录: {result['count']}条")
    for r in result['records']:
        print(f"  {r['date']} [{r['severity']}] {r['title'][:60]}")
