# -*- coding: utf-8 -*-
"""
四市场实时行情模块（A股/北交所/港股/美股）
数据源: 腾讯行情接口 (qt.gtimg.cn)

✅ 傻瓜式自动识别 —— 无需指定市场，代码自动识别：
  - 纯字母代码（AAPL, MSFT）        → 美股 us
  - 4-5位数字（00700, 06606）       → 港股 hk
  - 92xxx（920262）                  → 北交所 bj
  - 6xxxx（600519）                   → A股沪市 sh
  - 0xxxx/3xxxx（000001, 300750）     → A股深市 sz

手动指定 market 参数仍然有效：fetch_price('AAPL') = fetch_price('AAPL', market='us')

使用示例:
  fetch_price('600519')              # A股，自动识别
  fetch_price('920262')              # 北交所，自动识别
  fetch_price('00700')              # 港股，自动识别
  fetch_price('AAPL')               # 美股，自动识别 ✅
  fetch_price('AAPL', market='hk')  # 强制当港股
"""
import urllib.request, re
from typing import Optional, List

# ── 安全校验 ──────────────────────────────────────────────────────────────
_CODE_PATTERN = re.compile(r'^[a-zA-Z0-9]{1,12}$')          # 通用白名单
_MARKET_WHITE = frozenset({'a', 'hk', 'bse', 'us', 'sh', 'sz', 'auto'})

def _validate_code(code: str) -> bool:
    """股票代码安全校验：仅允许字母数字，长度1-12"""
    return bool(_CODE_PATTERN.match(code))

def _validate_market(market: str) -> bool:
    """市场参数白名单校验"""
    return market in _MARKET_WHITE

def _validate_codes(codes: List[str], market: str = 'a') -> tuple:
    """批量校验，返回 (有效列表, 错误列表)"""
    if not _validate_market(market):
        return [], [f'illegal_market:{market}']
    valid, invalid = [], []
    for c in codes:
        if _validate_code(c):
            valid.append(c)
        else:
            invalid.append(c)
    return valid, invalid


def _format_tencent_datetime(raw_dt: str) -> str:
    """将腾讯行情时间戳统一格式化为 'YYYY-MM-DD HH:MM:SS'
    支持格式: 14位纯数字(20260424153952), 8位日期(20260424), 日期/时间混合(2026/04/24 16:08:34)
    不合法则返回空串（交由调用方 fallback）
    """
    if not raw_dt or raw_dt in ('?', '0', ''):
        return ''
    # 优先尝试含分隔符的日期格式: 2026/04/24 16:08:34
    m = re.match(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s*(\d{1,2}):(\d{2})(?::(\d{2}))?', raw_dt)
    if m:
        y, mo, d, h, mi, s = m.groups()
        mo, d, h = mo.zfill(2), d.zfill(2), h.zfill(2)
        s = s or '00'
        return f'{y}-{mo}-{d} {h}:{mi}:{s}'
    # 提取连续数字
    digits = re.sub(r'[^0-9]', '', raw_dt)
    if len(digits) >= 14:
        y, mo = digits[:4], digits[4:6]
        if 1 <= int(mo) <= 12:  # 月份校验
            return f'{digits[:4]}-{digits[4:6]}-{digits[6:8]} {digits[8:10]}:{digits[10:12]}:{digits[12:14]}'
    elif len(digits) >= 8:
        y, mo = digits[:4], digits[4:6]
        if 1 <= int(mo) <= 12:  # 月份校验
            return f'{digits[:4]}-{digits[4:6]}-{digits[6:8]}'
    return ''  # 不合法，返回空串


def _pick_datetime(fields: list) -> str:
    """从腾讯行情 fields 中提取时间戳，依次尝试 [29] 和 [30]，返回首个合法格式化时间"""
    for idx in (29, 30):
        if len(fields) > idx and fields[idx]:
            dt = _format_tencent_datetime(fields[idx])
            if dt:
                return dt
    return ''


def _format_cap(raw: str) -> Optional[str]:
    """格式化市值
    腾讯行情 field[45] 原始单位是「亿元」
    输出优先用 万亿/亿，保留2位小数，失败返回None
    """
    try:
        val = float(raw)  # 单位：亿元
        if val >= 10000:
            return f'{val/10000:.2f}万亿'   # ≥1万亿
        elif val >= 1:
            return f'{val:.2f}亿'           # ≥1亿
        else:
            return f'{val*10000:.2f}万'     # <1亿
    except (ValueError, TypeError):
        return None


def infer_market(code: str) -> str:
    """根据股票代码特征自动推断市场，无需手动指定
    
    判断顺序（从最特殊到最通用）：
      1. 纯字母 → 美股（纯数字/混合都不行）
      2. 4-5位纯数字 → 港股（A股是6位，6开头另归沪市）
      3. 92xxx → 北交所（A股没有92开头）
      4. 6xxxx → A股沪市
      5. 其余(0/3/8xxxx) → A股深市
    """
    code = code.strip()
    # 1. 纯字母 = 美股（A股/港股代码都是数字）
    if code.isalpha():
        return 'us'
    # 2. 4-5位纯数字 = 港股（6位=A股，92xxx另归北交所）
    if re.match(r'^\d{4,5}$', code):
        return 'hk'
    # 3. 北交所 92xxx（A没92，深交所有但走sz）
    if code.startswith('92'):
        return 'bse'
    # 4. A股沪市 6开头
    if code.startswith('6'):
        return 'a'
    # 5. 其余(0/1/3/8开头) → A股深市/北交所8开头
    return 'a'


def get_symbol(code: str, market: str = 'a') -> str:
    """生成腾讯行情接口代码格式（输入已通过校验）
    港股自动识别：4-5位纯数字代码自动归为港股
    北交所自动识别：92开头自动归为北交所
    """
    code = code.strip()
    # 港股自动识别：4-5位纯数字（腾讯API用hk前缀）
    if re.match(r'^\d{4,5}$', code):
        return f'hk{code}'
    # 北交所自动识别（92开头）
    if code.startswith('92'):
        return f'bj{code}'
    if market == 'hk':
        return f'hk{code}'
    if market == 'us':
        return f'us{code}'
    if market == 'bse':
        return f'bj{code}'
    # A股: 6开头=sh, 其他=sz
    prefix = 'sh' if code.startswith('6') else 'sz'
    return f'{prefix}{code}'


def fetch_price(stock_codes, market: str = 'auto', data_dir=None) -> dict:
    """
    获取四市场实时行情（支持单只或逗号分隔多只）

    Args:
        stock_codes: 股票代码或逗号分隔的代码列表
        market: 'auto'(默认)='a'/'hk'/'bse'/'us' 自动识别
               - 'a'   强制A股（用于批量混查时兜底）
               - 'hk'  强制港股
               - 'bse' 强制北交所
               - 'us'  强制美股

    Returns:
        单只时返回 dict，多只时返回 list[dict]
        新增字段: pe(市盈率), market_cap(总市值)
    """
    # ── 自动推断市场（当 market='auto' 时）───────────────────────────────
    # 统一转字符串（兼容传入列表的旧用法）
    if isinstance(stock_codes, (list, tuple)):
        stock_codes = ','.join(str(c) for c in stock_codes)

    if market == 'auto':
        # 从第一个有效代码推断整体市场（用于批量场景）
        first_code = str(stock_codes).split(',')[0].strip()
        market = infer_market(first_code)

    # 单只要不要校验
    single_mode = not (isinstance(stock_codes, str) and ',' in stock_codes)
    if single_mode:
        code_str = str(stock_codes)
        # 单只：自动推断市场（覆盖默认的 'a'）
        if market == 'auto':
            market = infer_market(code_str)
        if not _validate_code(code_str) or not _validate_market(market):
            return {'stock_code': code_str, 'status': 'invalid_input', 'message': '非法股票代码或市场参数'}
    else:
        valid_codes, invalid = _validate_codes(
            [c.strip() for c in stock_codes.split(',') if c.strip()], market)
        if invalid:
            return {'status': 'error', 'message': f'非法代码: {invalid}'}
        if not valid_codes:
            return {'status': 'error', 'message': '股票代码为空'}

    # 支持逗号分隔的批量查询
    if isinstance(stock_codes, str) and ',' in stock_codes:
        codes = valid_codes
        symbols = [get_symbol(c, market) for c in codes]
        url = f'https://qt.gtimg.cn/q={chr(44).join(symbols)}'
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://finance.qq.com/'
            })
            r = urllib.request.urlopen(req, timeout=15)
            raw = r.read().decode('gbk', errors='replace')
        except Exception as e:
            return [{'stock_code': c, 'status': f'error: {str(e)[:50]}'} for c in codes]
        results = []
        for sym, code in zip(symbols, codes):
            m = re.search(rf'v_{re.escape(sym)}="([^"]+)"', raw)
            if not m:
                results.append({'stock_code': code, 'symbol': sym, 'status': 'not_found', 'name': None, 'price': None, 'chg': None, 'pct': None})
                continue
            fields = m.group(1).split('~')
            name = fields[1] if len(fields) > 1 else ''
            if name in ('', 'pv_none_match', 'none') or 'none' in raw.lower() and 'v_' + sym not in raw:
                results.append({'stock_code': code, 'symbol': sym, 'status': 'not_found', 'name': None, 'price': None, 'chg': None, 'pct': None})
            else:
                results.append({
                    'stock_code': code, 'symbol': sym,
                    'name': name,
                    'price': fields[3] if len(fields) > 3 and fields[3] else None,
                    'prev_close': fields[4] if len(fields) > 4 and fields[4] else None,
                    'open': fields[5] if len(fields) > 5 and fields[5] else None,
                    'high': fields[33] if len(fields) > 33 and fields[33] else None,
                    'low': fields[34] if len(fields) > 34 and fields[34] else None,
                    'chg': fields[31] if len(fields) > 31 and fields[31] else None,
                    'pct': fields[32] if len(fields) > 32 and fields[32] else None,
                    'vol_hands': fields[6] if len(fields) > 6 and fields[6] else None,
                    'datetime': _pick_datetime(fields),
                    'pe': fields[39] if len(fields) > 39 and fields[39] and fields[39] not in ('-', '', '?') else None,
                    'market_cap': _format_cap(fields[45]) if len(fields) > 45 and fields[45] else None,
                    'status': 'trading', 'market': market
                })
        return results

    # ── 单只查询（原有逻辑）──
    stock_code = stock_codes  # 兼容命名
    result = {
        'stock_code': stock_code,
        'market': market,
        'source': f'Tencent qt.gtimg.cn ({market})',
        'name': None, 'price': None, 'prev_close': None, 'open': None,
        'high': None, 'low': None, 'chg': None, 'pct': None,
        'vol_hands': None, 'datetime': None, 'status': 'unknown', 'raw': None,
    }

    symbol = get_symbol(stock_code, market)
    url = f'https://qt.gtimg.cn/q={symbol}'

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.qq.com/'
        })
        r = urllib.request.urlopen(req, timeout=10)
        raw = r.read().decode('gbk', errors='replace')
        result['raw'] = raw[:200]

        m = re.search(rf'v_{symbol}="([^"]+)"', raw)
        if not m:
            result['status'] = 'not_found'
            return result

        fields = m.group(1).split('~')
        if len(fields) < 35:
            result['status'] = 'parse_error'
            return result

        name = fields[1]
        if name in ('', 'pv_none_match', 'none') or 'none' in raw.lower():
            result['status'] = 'not_found'
            return result

        result['name'] = name
        result['price'] = fields[3] if fields[3] else None
        result['prev_close'] = fields[4] if fields[4] else None
        result['open'] = fields[5] if fields[5] else None
        result['high'] = fields[33] if fields[33] else None
        result['low'] = fields[34] if fields[34] else None
        result['vol_hands'] = fields[6] if fields[6] else None
        result['chg'] = fields[31] if len(fields) > 31 and fields[31] else None
        result['pct'] = fields[32] if len(fields) > 32 and fields[32] else None
        result['datetime'] = _pick_datetime(fields)
        # PE(市盈率) 和市值（tjefferson/stock-price-query 来源）
        result['pe'] = fields[39] if len(fields) > 39 and fields[39] and fields[39] not in ('-', '', '?') else None
        result['market_cap'] = _format_cap(fields[45]) if len(fields) > 45 and fields[45] else None

        # 判断停牌（港股/A股/北交所字段格式略有不同）
        try:
            if market == 'hk':
                vol = float(fields[6]) if fields[6] else 0
                chg_hk = float(fields[31]) if len(fields) > 31 and fields[31] else None
                result['status'] = 'trading' if (vol > 0 and chg_hk is not None) else 'suspended'
            else:
                vol = int(float(fields[6])) if fields[6] else 0
                high_val = float(fields[33]) if fields[33] else 0
                low_val = float(fields[34]) if fields[34] else 0
                result['status'] = 'suspended' if (vol == 0 or (high_val == 0 and low_val == 0)) else 'trading'
        except (ValueError, TypeError):
            result['status'] = 'unknown'

        return result

    except Exception as e:
        result['status'] = f'error: {str(e)[:50]}'
        return result


# ── market_label 辅助 ───────────────────────────────────────────────────────────
MARKET_MAP = {'a': 'A股', 'hk': '港股', 'bse': '北交所', 'us': '美股', 'sh': '沪市', 'sz': '深市'}

def market_label(market: str) -> str:
    """返回市场中文标签，兜底返回原值"""
    return MARKET_MAP.get(market, market)


# ---------- 兼容旧接口 ----------
def fetch_bse_price(stock_code: str, data_dir=None) -> dict:
    """兼容旧接口: 默认当作北交所处理（仅保留，提示用户改用fetch_price）"""
    return fetch_price(stock_code, market='bse', data_dir=data_dir)


def format_price(result: dict) -> str:
    """格式化行情输出"""
    if not result or result.get('status') == 'not_found':
        return f"  (股票 {result.get('stock_code', '???')} 无实时数据)"

    name = result.get('name') or '?'
    price = result.get('price') or '?'
    chg = result.get('chg') or '?'
    pct = result.get('pct') or '?'
    high = result.get('high') or '?'
    low = result.get('low') or '?'
    open_ = result.get('open') or '?'
    prev = result.get('prev_close') or '?'
    vol = result.get('vol_hands') or '?'
    dt = result.get('datetime') or ''
    status = result.get('status', 'unknown')
    pe = result.get('pe')
    mktcap = result.get('market_cap')
    mkt_label = market_label(result.get('market', ''))

    try:
        chg_val = float(chg) if chg and str(chg) != '?' else 0
        pct_val = float(pct) if pct and str(pct) != '?' else 0
        chg_str = f'{chg_val:+.2f}'
        pct_str = f'{pct_val:+.2f}%'
    except (ValueError, TypeError):
        chg_str = str(chg)
        pct_str = f'{pct}%' if pct and str(pct) != '?' else '?'

    emoji = {'trading': '📈', 'suspended': '💤', 'not_found': '❓'}.get(status, '❓')

    lines = [
        f'{emoji} {mkt_label}实时行情',
        f'  股票: {name}({result.get("stock_code")}) [{status}]',
        f'  现价: {price}  涨跌: {chg_str}({pct_str})',
        f'  今开: {open_}  昨收: {prev}',
        f'  最高: {high}  最低: {low}',
        f'  成交量: {vol} 手',
        f'  更新时间: {dt}',
    ]
    if pe:
        lines.append(f'  市盈率(PE): {pe}')
    if mktcap:
        lines.append(f'  总市值: {mktcap}')
    lines.append(f'  数据源: 腾讯行情')
    return '\n'.join(lines)


# ---------- 别名 ----------
format_bse_price = format_price


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python bse_price.py <code> [market]')
        print('  market: a=A股(默认) hk=港股 bse=北交所 us=美股')
        sys.exit(0)
    code = sys.argv[1]
    market = sys.argv[2] if len(sys.argv) > 2 else 'a'
    r = fetch_price(code, market)
    print(format_price(r))
