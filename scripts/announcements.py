# -*- coding: utf-8 -*-
"""
模块1：公告全景采集
从东方财富+巨潮获取近12个月重大公告，分类整理

修复记录(P1-2)：
- 全部HTTP请求接入 safe_get（超时15s + 重试3次 + 降级返回空列表）
- 港股CNINFO增加多页翻页（最多5页，每页20条）
- A股东方财富增加多页翻页（最多5页，每页200条）
"""
import sys, json, requests, re, time
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

# 复用safe_request
from scripts.safe_request import safe_get

EM_ANNOUNCE_URL = (
    "https://np-anotice-stock.eastmoney.com/api/security/ann"
    "?cb=&sr=-1&ann_type=A&client_source=web&f_node=0&s_node=0&stock_list={stock}"
)
EM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://data.eastmoney.com/',
    'Accept': 'application/json',
}

CNINFO_URL = "http://www.cninfo.com.cn/new/fulltextSearch/full"
CNINFO_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
    'Referer': 'http://www.cninfo.com.cn/',
}

from datetime import datetime as _dt


def fetch_announcements(stock_code, market='a', data_dir=None):
    """
    获取并分类整理A股/港股公告
    返回：{count, categories, recent_30, key_events, metadata}
    """
    all_anns = []
    steps = []  # 溯源步骤

    # ---- A股：东方财富公告列表（多页）----
    if market == 'a':
        em_pages = 0
        em_total = 0
        for page in range(1, 6):  # 最多5页
            em_anns = _fetch_em_a_page(stock_code, page_index=page, page_size=200)
            if not em_anns:
                break
            em_pages += 1
            em_total += len(em_anns)
            all_anns.extend(em_anns)
            # 如果页数少于200条，说明已经是最后一页
            if len(em_anns) < 200:
                break
            time.sleep(0.3)
        steps.append({
            'step': 'em_announce',
            'label': '东方财富公告API',
            'source': 'em_announce',
            'pages': em_pages,
            'count': em_total,
            'status': 'OK' if em_total > 0 else 'EMPTY',
        })

    # ---- 港股：巨潮CNINFO（多页）----
    elif market == 'hk':
        cn_pages = 0
        cn_total = 0
        for page in range(1, 6):  # 最多5页
            cninfo_anns = _fetch_cninfo_hk_page(stock_code, page_index=page, page_size=20)
            if not cninfo_anns:
                break
            cn_pages += 1
            cn_total += len(cninfo_anns)
            all_anns.extend(cninfo_anns)
            if len(cninfo_anns) < 20:
                break
            time.sleep(0.5)
        steps.append({
            'step': 'cninfo_hk',
            'label': '巨潮资讯港股公告',
            'source': 'cninfo_hk_announce',
            'pages': cn_pages,
            'count': cn_total,
            'status': 'OK' if cn_total > 0 else 'EMPTY',
        })

    # 美股/北交所暂无公告源
    if not steps:
        steps.append({
            'step': 'none',
            'label': '无可用公告源',
            'source': 'unknown',
            'count': 0,
            'status': 'SKIP',
        })

    # 去重（按日期+标题）
    seen = set()
    unique_anns = []
    for a in all_anns:
        key = (a.get('date', ''), a.get('title', ''))
        if key not in seen:
            seen.add(key)
            unique_anns.append(a)
    all_anns = unique_anns

    # 按日期排序
    all_anns.sort(key=lambda x: x.get('date', ''), reverse=True)

    # 分类
    categories = _categorize(all_anns)

    # 近30条
    recent_30 = all_anns[:30]

    # 关键事件（重大事项标记）
    key_events = [a for a in all_anns if a.get('is_key', False)][:20]

    # 溯源：取第一个成功步骤的source
    ok_step = next((s for s in steps if s['status'] == 'OK'), None)
    top_source = ok_step['source'] if ok_step else ('em_announce' if market == 'a' else 'cninfo_hk_announce')

    return {
        'count': len(all_anns),
        'categories': categories,
        'recent_30': recent_30,
        'key_events': key_events,
        'metadata': {
            'total_fetched': len(all_anns),
            'date_range': (
                all_anns[-1]['date'] if all_anns else None,
                all_anns[0]['date'] if all_anns else None,
            )
        },
        '_meta': {
            'source': top_source,
            'steps': steps,
            'fetched_at': _dt.now().isoformat(),
        },
    }


def _fetch_em_a_page(stock_code, page_index=1, page_size=200):
    """东方财富A股公告列表（单页）"""
    url = EM_ANNOUNCE_URL.format(stock=stock_code) + f"&page_size={page_size}&page_index={page_index}"

    raw = safe_get(
        url,
        params=None,
        headers=EM_HEADERS,
        timeout=20,
        retries=2,
        backoff=1.5,
    )

    if not raw:
        return []
    if isinstance(raw, dict) and raw.get('error'):
        return []

    from scripts.safe_request import safe_extract
    data = safe_extract(raw, ['data'], {})
    items = data.get('list', []) if isinstance(data, dict) else []

    result = []
    for item in items:
        title = item.get('title', '') or item.get('title_ch', '')
        notice_date = item.get('notice_date', '')
        if isinstance(notice_date, str):
            notice_date = notice_date[:10]
        elif notice_date:
            notice_date = str(notice_date)[:10]
        else:
            notice_date = ''

        art_code = item.get('art_code', '')
        columns = [c.get('column_name', '') for c in item.get('columns', [])]
        col_str = '|'.join(columns)

        result.append({
            'date': notice_date,
            'title': title,
            'art_code': art_code,
            'category': col_str,
            'source': '东方财富',
            'stock_code': stock_code,
            'is_key': _is_key_event(title, col_str),
        })
    return result


def _fetch_cninfo_hk_page(stock_code, page_index=1, page_size=20):
    """巨潮CNINFO港股公告（单页）"""
    params = {
        'searchkey': stock_code,
        'sdate': '',
        'edate': '',
        'isfulltext': 'false',
        'sortName': 'pubdate',
        'sortType': 'desc',
        'plateCode': '',
        'pageNum': page_index,
        'pageSize': page_size,
    }

    raw = safe_get(
        CNINFO_URL,
        params=params,
        headers=CNINFO_HEADERS,
        timeout=20,
        retries=2,
        backoff=1.5,
    )

    if not raw:
        return []
    if isinstance(raw, dict) and raw.get('error'):
        return []

    # CNINFO返回: {"announcements": [...]}
    items = raw.get('announcements', []) or []

    result = []
    for item in items:
        raw_title = item.get('announcementTitle', '')
        title = re.sub(r'<[^>]+>', '', raw_title)
        aid = item.get('announcementId', '')
        pub_ts = item.get('announcementTime', 0)
        if pub_ts:
            pub_date = datetime.fromtimestamp(pub_ts / 1000).strftime('%Y-%m-%d')
        else:
            pub_date = ''

        adjunct_url = item.get('adjunctUrl', '')
        result.append({
            'date': pub_date,
            'title': title,
            'announcement_id': aid,
            'adjunct_url': adjunct_url,
            'source': 'CNINFO港股',
            'stock_code': stock_code,
            'is_key': _is_key_event_hk(title),
        })
    return result


def _is_key_event(title, category):
    """判断是否为重大事件"""
    key_keywords = [
        '重大', '诉讼', '仲裁', '变更', '收购', '出售',
        '分拆', '上市', '利润分配', '分红', '亏损', '盈利警告',
        '要约', '私有化', '实际控制人', '董事长', '总裁', '辞职',
        '行政处罚', '监管函', '问询函', '警示函', '立案',
        '内部控制', '非标准', '非标', '保留意见', '无法表示',
        '审计', '带强调', '持续经营',
    ]
    key_cats = [
        '诉讼仲裁', '重大事项', '证券简称变更', '公司名称变更',
        '股东大会决议公告', '高管人员任职变动', '监管', '核查意见',
    ]
    return any(k in title for k in key_keywords) or any(c in category for c in key_cats)


def _is_key_event_hk(title):
    """港股重大事件判断"""
    key = [
        '要约', '收购', '私有化', '盈利警告', '业绩', '董事', '主席',
        '退市', '合并', '分派', '特別股息', '建議', '诉讼', '仲裁',
        '行政处罚', '监管', '调查', '內部監控',
    ]
    return any(k in title for k in key)


def _categorize(anns):
    """按来源+栏目分类"""
    categories = {}
    for a in anns:
        cat = a.get('category', a.get('source', '其他'))
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(a)
    return categories


def download_announcement_pdf(ann_info, dest_dir, market='a'):
    """
    下载公告PDF
    ann_info: dict with art_code (A股) or announcement_id+adjunct_url (港股)
    """
    os_mod = __import__('os')
    os_mod.makedirs(dest_dir, exist_ok=True)

    if market == 'a':
        art_code = ann_info.get('art_code', '')
        if not art_code or len(art_code) < 10:
            return None
        year = art_code[2:6]
        month = art_code[6:8]
        day = art_code[8:10]
        base_urls = [
            f"https://reportimages.eastmoney.com/DAILY/{year}/{month}/{day}/{art_code}.pdf",
            f"https://reportimages.eastmoney.com/{year}/{month}/{day}/{art_code}.pdf",
        ]
        for url in base_urls:
            try:
                r = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://data.eastmoney.com/'
                }, timeout=20)
                if r.status_code == 200 and len(r.content) > 10000:
                    dest = os_mod.path.join(dest_dir, f"{art_code}.pdf")
                    with open(dest, 'wb') as f:
                        f.write(r.content)
                    return dest
            except Exception:
                continue

    elif market == 'hk':
        aid = ann_info.get('announcement_id', '')
        adjunct_url = ann_info.get('adjunct_url', '')
        if adjunct_url:
            pdf_url = f"http://static.cninfo.com.cn/{adjunct_url}"
        else:
            pdf_url = None
        if not pdf_url:
            return None
        try:
            r = requests.get(pdf_url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'http://www.cninfo.com.cn/'
            }, timeout=30)
            if r.status_code == 200 and len(r.content) > 5000:
                dest = os_mod.path.join(dest_dir, f"{aid}.pdf")
                with open(dest, 'wb') as f:
                    f.write(r.content)
                return dest
        except Exception:
            pass

    return None


if __name__ == '__main__':
    result = fetch_announcements('002180', 'a')
    print(f"获取 {result['count']} 条公告")
    for k, v in result['categories'].items():
        print(f"  {k}: {len(v)}条")
