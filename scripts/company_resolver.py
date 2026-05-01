# -*- coding: utf-8 -*-
"""
company_resolver.py — 中文公司名跨市场智能识别

用法:
    python analyze.py --name "腾讯"                    # 搜索并分析
    python analyze.py --name "比亚迪" --dims quote     # 自动识别A股+港股

搜索策略:
    A股/北交所 → AKShare stock_info_a_code_name (精确匹配)
    港股       → 东方财富公司搜索API + AKShare港股列表
    美股       → Yahoo Finance搜索(中文/拼音/英文)
    跨市场去重 → 同一人群通/实控人/英文名匹配
"""
import sys, re, json
sys.path.insert(0, '.')

import requests
import akshare as ak
from datetime import datetime

# ─── 工具函数 ───────────────────────────────────────────

def safe_call(fn, *args, **kwargs):
    """优雅降级：函数调用失败返回 None"""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return None


def normalize(s):
    """字符串归一化：去空格、转小写、移除括号内容"""
    if not s:
        return ''
    s = re.sub(r'[\s　]+', '', str(s).strip().lower())
    s = re.sub(r'[(（【\[].*?[])】\]]', '', s)  # 去除括号内容
    return s


def name_match(name1, name2):
    """判断两个公司名是否可能指向同一公司"""
    n1 = normalize(name1)
    n2 = normalize(name2)
    if not n1 or not n2:
        return False
    # 完全相等
    if n1 == n2:
        return True
    # 一个包含另一个（短名包含于长名）
    if len(n1) >= 2 and len(n2) >= 2:
        if n1 in n2 or n2 in n1:
            return True
    # 前3个字相同
    if len(n1) >= 3 and len(n2) >= 3 and n1[:3] == n2[:3]:
        return True
    return False


# ─── 常用港股映射（加快匹配速度）
KNOWN_CHINESE_HK = {
    '腾讯': '00700', '腾讯控股': '00700',
    '阿里巴巴': '09988', '阿里': '09988',
    '美团': '03690',
    '小米': '01810', '小米集团': '01810',
    '快手': '01024',
    '京东': '09618',
    '拼多多': 'PDD',  # 美股为主
    '网易': '09999',
    '百度': '09888',
    '哔哩哔哩': '09626', 'B站': '09626',
    '比亚迪': '01211',
    '长城汽车': '02333',
    '吉利汽车': '00175',
    '小鹏汽车': '09868',
    '理想汽车': '02015',
    '蔚来': '09866',
    '宁德时代': '未上市',
    '新东方': '09901',
    '海底捞': '06862',
    '颐海国际': '01579',
    '华润啤酒': '00291',
    '青岛啤酒': '00168',
    '蒙牛乳业': '02319',
    '安踏体育': '02020',
    '李宁': '02331',
    '波司登': '03998',
    '申洲国际': '02313',
    '舜宇光学': '02382',
    '瑞声科技': '02018',
    '中芯国际': '00981',
    '华虹半导体': '01347',
    '药明生物': '02269',
    '药明康德': '02359',
    '中国生物制药': '01177',
    '石药集团': '01093',
    '翰森制药': '03692',
    '金斯瑞生物': '01548',
    '信达生物': '01801',
    '百济神州': '06160',
    '君实生物': '01877',
    '复星医药': '02196',
    '中国平安': '02318',
    '招商银行': '03968',
    '工商银行': '01398',
    '建设银行': '00939',
    '中国银行': '03988',
    '农业银行': '01288',
    '邮储银行': '01658',
    '交通银行': '03328',
    '中信证券': '06030',
    '中金公司': '03908',
    '香港交易所': '00388', '港交所': '00388',
    '中国移动': '00941',
    '中国电信': '00728',
    '中国联通': '00762',
    '中国石油': '00857', '中石油': '00857',
    '中国石化': '00386', '中石化': '00386',
    '中海油': '00883',
    '中国神华': '01088',
    '兖矿能源': '01171',
    '中国铝业': '02600',
    '江西铜业': '00358',
    '紫金矿业': '02899',
    '中国恒大': '03333',
    '融创中国': '01918',
    '碧桂园': '02007',
    '万科企业': '02202',
    '龙湖集团': '00960',
    '华润置地': '01109',
    '中国海外发展': '00688',
}


def fuzzy_match(cand_name, query):
    """模糊匹配：query是cand_name的子串，或反之"""
    q = normalize(query)
    c = normalize(cand_name)
    if not q or not c:
        return False
    # query是cand的子串
    if q in c:
        return True
    # cand是query的子串（query更短）
    if c in q:
        return True
    # 前3个字相同
    if len(q) >= 3 and len(c) >= 3 and q[:3] == c[:3]:
        return True
    return False


# ─── 各市场搜索 ─────────────────────────────────────────

def search_a_share(query):
    """
    A股搜索：使用AKShare获取全量A股代码-名称映射，精确匹配
    返回: [{stock, name, market('a'/'bse'), prefix}, ...]
    """
    print(f"  [A股] 搜索 '{query}'...")
    result = safe_call(ak.stock_info_a_code_name)
    if result is None or result.empty:
        return []
    
    matches = []
    q = normalize(query)
    
    for _, row in result.iterrows():
        code = str(row.get('code', '')).strip()
        name = str(row.get('name', '')).strip()
        if not code or not name:
            continue
        
        n_name = normalize(name)
        # 精确匹配
        if n_name == q:
            market = 'bse' if code.startswith('92') else 'a'
            matches.insert(0, {'stock': code, 'name': name, 'market': market, 
                               'source': 'akshare_a', 'confidence': 100})
        # 模糊匹配
        elif fuzzy_match(name, query):
            market = 'bse' if code.startswith('92') else 'a'
            matches.append({'stock': code, 'name': name, 'market': market,
                           'source': 'akshare_a', 'confidence': 80})
    
    return matches


def search_hk_stock(query):
    """
    港股搜索：快速映射 + 东方财富API
    返回: [{stock, name, market:'hk'}, ...]
    """
    print(f"  [港股] 搜索 '{query}'...")
    matches = []
    q = normalize(query)
    
    # 方法0: 快速映射（优先，避免API调用）
    for cn_name, hk_code in KNOWN_CHINESE_HK.items():
        if normalize(cn_name) == q:
            matches.insert(0, {'stock': hk_code, 'name': cn_name, 'market': 'hk',
                              'source': 'known_chinese_hk', 'confidence': 100})
            break
        elif fuzzy_match(cn_name, query):
            matches.append({'stock': hk_code, 'name': cn_name, 'market': 'hk',
                           'source': 'known_chinese_hk', 'confidence': 90})
    
    if matches:
        # 去重
        seen = {}
        for m in matches:
            key = m['stock']
            if key not in seen or m['confidence'] > seen[key]['confidence']:
                seen[key] = m
        return list(seen.values())
    
    # 方法1: 东方财富港股搜索API（优先，快速）
    try:
        url = 'https://searchapi-hk.eastmoney.com/bussiness/web/GetHKStockList'
        params = {'keyword': query, 'pageSize': 20}
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.eastmoney.com/'}
        r = requests.get(url, params=params, timeout=10, headers=headers)
        data = r.json()
        
        items = data.get('result', {}).get('data', []) or []
        for item in items[:10]:
            code = str(item.get('code', '')).strip()
            name = str(item.get('name', '')).strip()
            if not code or not name:
                continue
            if normalize(name) == q:
                matches.insert(0, {'stock': code, 'name': name, 'market': 'hk',
                                  'source': 'em_hk_api', 'confidence': 100})
            elif fuzzy_match(name, query):
                matches.append({'stock': code, 'name': name, 'market': 'hk',
                               'source': 'em_hk_api', 'confidence': 80})
        if matches:
            # 去重
            seen = {}
            for m in matches:
                key = m['stock']
                if key not in seen or m['confidence'] > seen[key]['confidence']:
                    seen[key] = m
            return list(seen.values())
    except Exception as e:
        print(f"    ⚠️ 东方财富港股API失败: {e}")

    # 方法2: AKShare港股列表（备用，较慢）
    # 只在前一种方法失败时使用
    try:
        hk_list = safe_call(ak.stock_hk_spot_em)
        if hk_list is not None and not hk_list.empty:
            # 先精确匹配
            for _, row in hk_list.iterrows():
                code = str(row.get('代码', '') or row.get('code', '')).strip()
                name = str(row.get('名称', '') or row.get('name', '')).strip()
                if not code or not name:
                    continue
                if normalize(name) == q:
                    matches.insert(0, {'stock': code, 'name': name, 'market': 'hk',
                                      'source': 'akshare_hk', 'confidence': 100})
                    break  # 精确匹配，直接返回
            
            # 如果没有精确匹配，再做模糊匹配（限制最多50条）
            if not matches:
                count = 0
                for _, row in hk_list.iterrows():
                    if count >= 50:  # 限制迭代次数
                        break
                    count += 1
                    code = str(row.get('代码', '') or row.get('code', '')).strip()
                    name = str(row.get('名称', '') or row.get('name', '')).strip()
                    if not code or not name:
                        continue
                    if fuzzy_match(name, query):
                        matches.append({'stock': code, 'name': name, 'market': 'hk',
                                       'source': 'akshare_hk', 'confidence': 80})
    except Exception as e:
        print(f"    ⚠️ AKShare港股列表搜索失败: {e}")

    # 去重（同名保留最高confidence）
    seen = {}
    for m in matches:
        key = m['stock']
        if key not in seen or m['confidence'] > seen[key]['confidence']:
            seen[key] = m
    return list(seen.values())


def search_us_stock(query):
    """
    美股搜索：Yahoo Finance搜索API（支持中文名/拼音/英文）
    返回: [{stock, name, market:'us'}, ...]
    """
    print(f"  [美股] 搜索 '{query}'...")
    matches = []
    q = normalize(query)
    
    # 常见中概股映射（hardcode最常见的，避免API依赖）
    KNOWN_CHINESE_US = {
        '阿里巴巴': 'BABA', '阿里': 'BABA',
        '腾讯音乐': 'TME',
        '百度': 'BIDU',
        '京东': 'JD',
        '拼多多': 'PDD',
        '网易': 'NTES',
        '哔哩哔哩': 'BILI', 'B站': 'BILI', 'bilibili': 'BILI',
        '小鹏汽车': 'XPEV',
        '理想汽车': 'LI',
        '蔚来': 'NIO',
        '比亚迪': 'BYDDF',  # 港股代码1211，ADR用BYDDF
        '比亚迪股份': 'BYDDF',
        '美团': 'MPNGY',
        '招商银行': 'CIHKY',
        '工商银行': 'ICBK',
        '中国银行': 'BACHY',
        '建设银行': 'CICHY',
        '农业银行': 'ACGBY',
        '中国人寿': 'LFC',
        '中国平安': 'PNGZF', '平安': 'PNGZF',
        '中国石油': 'PTR',
        '中国石化': 'SHI',
        '中石化': 'SHI',
        '中石油': 'PTR',
        '中国建筑': 'CICHY',
        '贵州茅台': 'MO',  # 茅台ADR
        '海底捞': 'HDL',
        '华住集团': 'HTHT',
        '新东方': 'EDU',
        '好未来': 'TAL',
        '学而思': 'TAL',
        '中信证券': 'CTSH',  # 无直接ADR，用CTH
        '中金公司': 'CICC',
        '宁德时代': '300750',  # 无ADR
        '小米': 'XIACY', '小米集团': 'XIACY',
        '快手': 'KUAISU',
        '微博': 'WB',
        '知乎': 'ZH',
        '满帮': 'YMM',
        'BOSS直聘': 'BZRP',
        '叮咚买菜': 'DL',
        '水滴': 'WDH',
        '汽车之家': 'ATHM',
        '陆金所': 'LU',
        '携程': 'TCOM',
        '前程无忧': 'JOBS',
        '猎聘': 'LPp',
        '红黄蓝': 'RYB',
        '万国数据': 'GDS',
        '世纪互联': 'VNET',
        '再鼎医药': 'ZLAB',
        '和黄医药': 'HCM',
        '百济神州': 'BGNE',
        '传奇生物': 'LEGN',
        '晶科能源': 'JKS',
        '大全新能源': 'DQ',
        '阿特斯太阳能': 'CSIQ',
        '天合光能': 'TSL',
        '晶澳科技': 'JASO',
        '南茂科技': 'IMOS',
        '中华电信': 'CHT',
        '台积电': 'TSM',
        '联发科': 'MEDI',
        '富士康': 'FXCOY',
        '鴻海': 'HNHPF',
    }
    
    # 精确匹配中文名→美股代码
    for cn_name, us_ticker in KNOWN_CHINESE_US.items():
        if normalize(cn_name) == q:
            matches.insert(0, {'stock': us_ticker, 'name': cn_name, 'market': 'us',
                             'source': 'known_chinese_us', 'confidence': 100})
            break
        elif fuzzy_match(cn_name, query):
            matches.append({'stock': us_ticker, 'name': cn_name, 'market': 'us',
                           'source': 'known_chinese_us', 'confidence': 80})
    
    # Yahoo Finance搜索（英文名/拼音）
    try:
        search_url = 'https://query1.finance.yahoo.com/v1/finance/search'
        params = {
            'q': query,
            'quotesCount': 10,
            'newsCount': 0,
            'enableFuzzyQuery': 'true',
        }
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(search_url, params=params, timeout=10, headers=headers)
        data = r.json()
        
        for item in data.get('quotes', [])[:10]:
            ticker = str(item.get('symbol', '')).strip()
            name = str(item.get('shortname', '') or item.get('longname', '')).strip()
            if not ticker:
                continue
            # 只保留普通股（排除期权/期货/ETF等）
            if '/' in ticker or '.' not in ticker:
                continue
            # 优先美股（.O/.N/.Q/.W结尾，或无后缀）
            suffix = ticker.split('.')[-1] if '.' in ticker else ''
            if suffix.upper() in ['OQ', 'N', 'Q', 'W', 'PK', ''] or suffix == suffix.upper():
                n_name = normalize(name)
                if n_name == q:
                    matches.insert(0, {'stock': ticker, 'name': name, 'market': 'us',
                                     'source': 'yahoo_search', 'confidence': 100})
                elif fuzzy_match(name, query):
                    # 避免重复
                    if not any(m['stock'] == ticker for m in matches):
                        matches.append({'stock': ticker, 'name': name, 'market': 'us',
                                       'source': 'yahoo_search', 'confidence': 75})
    except Exception as e:
        print(f"    ⚠️ Yahoo Finance搜索失败: {e}")
    
    # 去重
    seen = {}
    for m in matches:
        key = m['stock'].upper()
        if key not in seen or m['confidence'] > seen[key]['confidence']:
            seen[key] = m
    return list(seen.values())


def cross_market_dedup(all_matches):
    """
    跨市场去重：识别同一家公司在不同市场的上市
    返回: {
        'singleton': [{stock, name, market, source, confidence}],  # 每地唯一
        'groups': [{'company_name': str, 'listings': [match, ...]}, ...],  # 跨市场组合
    }
    """
    # 按公司名分组
    name_groups = {}
    for m in all_matches:
        name = m['name']
        if name not in name_groups:
            name_groups[name] = []
        name_groups[name].append(m)
    
    singleton = []
    groups = []
    
    for name, listings in name_groups.items():
        markets = set(l['market'] for l in listings)
        if len(listings) > 1 or len(markets) > 1:
            # 跨市场：同公司多地上市
            # 选每市场最佳匹配
            best_per_market = {}
            for l in listings:
                mkt = l['market']
                if mkt not in best_per_market or l['confidence'] > best_per_market[mkt]['confidence']:
                    best_per_market[mkt] = l
            groups.append({
                'company_name': name,
                'listings': list(best_per_market.values()),
            })
        else:
            singleton.append(listings[0])
    
    return {'singleton': singleton, 'groups': groups}


def resolve_company_name(query, verbose=True):
    """
    主入口：输入中文公司名，返回所有市场的匹配结果
    
    返回结构:
    {
        'query': str,
        'total': int,
        'has_multi_market': bool,
        'results': [
            {'stock': '600519', 'name': '贵州茅台', 'market': 'a',   'confidence': 100},
            {'stock': '00700',  'name': '腾讯控股', 'market': 'hk',  'confidence': 100},
            ...
        ],
        'groups': [  # 跨市场组合
            {
                'company_name': '比亚迪',
                'summary': 'A+H双地上市',
                'listings': [...]
            },
            ...
        ],
        'singletons': [...],  # 单市场唯一结果
    }
    """
    if verbose:
        print(f"\n🔍 公司名识别: '{query}'")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    # 并行搜索三市场
    import concurrent.futures
    
    all_matches = []
    errors = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        fut_a  = ex.submit(search_a_share,  query)
        fut_hk = ex.submit(search_hk_stock, query)
        fut_us = ex.submit(search_us_stock, query)
        
        for fut in concurrent.futures.as_completed([fut_a, fut_hk, fut_us]):
            try:
                result = fut.result()
                if result:
                    all_matches.extend(result)
            except Exception as e:
                errors.append(str(e))
    
    if verbose and errors:
        print(f"  ⚠️ 部分市场搜索失败: {errors}")
    
    # 去重 & 合并
    deduped = cross_market_dedup(all_matches)
    
    # 构建groups的summary
    for g in deduped['groups']:
        markets = [l['market'] for l in g['listings']]
        labels = {'a': 'A股', 'hk': '港股', 'us': '美股', 'bse': '北交所'}
        g['summary'] = '+'.join(labels.get(m, m) for m in markets) + '双/多地上市'
    
    total = len(deduped['singleton']) + len(deduped['groups'])
    
    result = {
        'query': query,
        'total': total,
        'has_multi_market': len(deduped['groups']) > 0,
        'all_results': all_matches,  # 原始全部结果
        'groups': deduped['groups'],
        'singletons': deduped['singleton'],
    }
    result['results'] = deduped['singleton'] + [l for g in deduped['groups'] for l in g['listings']]
    
    if verbose:
        print_result_summary(result)
    
    return result


def print_result_summary(result):
    """打印搜索结果摘要"""
    print(f"{'='*60}")
    print(f"  🔍 搜索结果: '{result['query']}'")
    print(f"  共找到 {result['total']} 个匹配项")
    print(f"{'─'*60}")
    
    if result['groups']:
        print(f"  📦 跨市场组合（同一公司多地上市）:")
        for g in result['groups']:
            print(f"    🏢 {g['company_name']} [{g['summary']}]")
            for l in g['listings']:
                mkt = {'a': 'A股', 'hk': '港股', 'us': '美股', 'bse': '北交所'}.get(l['market'], l['market'])
                conf_mark = '✅' if l['confidence'] >= 100 else '⚠️'
                print(f"      {conf_mark} {l['stock']:>10s}  ({mkt:>4s})  {l.get('source','')}")
    
    if result['singletons']:
        print(f"  📄 单市场匹配:")
        for l in result['singletons']:
            mkt = {'a': 'A股', 'hk': '港股', 'us': '美股', 'bse': '北交所'}.get(l['market'], l['market'])
            conf_mark = '✅' if l['confidence'] >= 100 else '⚠️'
            print(f"    {conf_mark} {l['stock']:>10s}  ({mkt:>4s})  {l['name']}  {l.get('source','')}")
    
    print(f"{'─'*60}")
    
    if result['has_multi_market']:
        print(f"  💡 提示: 该公司多地上市，建议使用 --dims quote 查看全部行情，")
        print(f"     或指定 --stock 特定代码 做深度分析")


def format_resolver_summary(result):
    """生成文本摘要（用于analyze.py的摘要行）"""
    if result['total'] == 0:
        return f"未找到任何匹配: '{result['query']}'"
    
    lines = [f"公司名识别: '{result['query']}' → "]
    
    if result['groups']:
        for g in result['groups']:
            listings_str = ', '.join(
                f"{l['stock']}({l['market']})" for l in g['listings']
            )
            lines.append(f"  🏢 {g['company_name']}: {listings_str}")
    
    for s in result['singletons']:
        mkt = {'a': 'A股', 'hk': '港股', 'us': '美股', 'bse': '北交所'}.get(s['market'], s['market'])
        lines.append(f"  📄 {s['stock']}({mkt}): {s['name']}")
    
    return '\n'.join(lines)


# ─── 快速测试 ─────────────────────────────────────────

if __name__ == '__main__':
    test_names = ['贵州茅台', '腾讯', '比亚迪', '宁德时代', '阿里巴巴', '苹果']
    for name in test_names:
        r = resolve_company_name(name)
        print()
