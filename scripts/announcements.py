# -*- coding: utf-8 -*-
"""
模块1：公告全景采集（增强版）
从东方财富+巨潮获取公告，按重要性分级，重要公告自动深挖+溯源

增强点：
- 三级分类：CRITICAL（自动提取）/ MAJOR（标记+可选提取）/ ROUTINE（仅列表）
- 基于column_code的精准分类（EM API层级编码）
- 重要公告自动下载PDF+提取关键内容
- 事件溯源：重要事件追溯历史关联公告

修复记录(P1-2)：
- 全部HTTP请求接入 safe_get（超时15s + 重试3次 + 降级返回空列表）
- 港股CNINFO增加多页翻页（最多5页，每页20条）
- A股东方财富增加多页翻页（最多5页，每页200条）
"""
import sys, json, requests, re, time, os, subprocess
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

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


# ============================================================
# 一、公告重要性分级体系
# ============================================================

# 重要性等级
CRITICAL = 'critical'   # 🔴 自动下载PDF + 提取关键内容 + 溯源
MAJOR = 'major'         # 🟡 标记重要性 + 可选提取
ROUTINE = 'routine'     # 🟢 仅列表展示

# EM column_code → 重要性 + 类型标签
# 层级结构：001=定期报告 002=公司大事 003=中介机构 05=其他
COLUMN_CODE_MAP = {
    # ── CRITICAL：必须深挖 ──
    '001002001':       (CRITICAL, '重大资产重组'),
    '001002002005':    (CRITICAL, '权益变动报告书'),
    '001002006001':    (CRITICAL, '收购/出售资产'),
    '001002006002':    (CRITICAL, '要约收购'),
    '001002006003':    (CRITICAL, '重大合同'),
    '001002006004':    (CRITICAL, '重大诉讼仲裁'),
    '001002007004004': (CRITICAL, '实际控制人变更'),
    '001002006014':    (CRITICAL, '诉讼仲裁'),
    '001002007001001':  (CRITICAL, '股权激励计划'),  # 计划草案
    '001002007001005':  (CRITICAL, '股权激励计划'),  # 激励计划
    '001002007001007001': (MAJOR, '股权激励进展'),  # 进展=MAJOR, 计划=CRITICAL
    '001002007003008':  (MAJOR, '回购/重组通知债权人'),  # EM误用：回购也放这里，降级为MAJOR
    '001002007003009001001': (MAJOR, '回购预案'),
    '001002007003009001002': (MAJOR, '回购方案修订'),
    '001002007003009002001': (MAJOR, '回购报告书'),
    '001002007003009004': (MAJOR, '回购进展情况'),
    '001002007003009005': (MAJOR, '回购实施公告'),

    # ── MAJOR：标记重点 ──
    '001002002001':    (MAJOR, '利润分配'),
    '001002002004':    (MAJOR, '股本变动'),
    '001002004001':    (MAJOR, '业绩预告'),
    '001002004013':    (MAJOR, '月度经营情况'),
    '001002005001001': (MAJOR, '证券简称变更'),
    '001002005001002': (MAJOR, '公司名称变更'),
    '001002005001008': (MAJOR, '高管/审计机构变更'),
    '001002005002':    (MAJOR, '高管人员任职变动'),
    '001002006005':    (MAJOR, '对外投资'),
    '001002006006':    (MAJOR, '借贷'),
    '001002006009':    (MAJOR, '资金占用'),
    '001002006011':    (MAJOR, '对外担保'),
    '001002006012':    (MAJOR, '募集资金'),
    '001002007002':    (MAJOR, '股份增减持'),
    '001002007003009': (MAJOR, '回购'),
    '001002007004001': (MAJOR, '股东增减持'),
    '001002007004002': (MAJOR, '股东/实控人增持'),
    '001002007004003': (MAJOR, '股东/实控人减持'),
    '001002007005':    (MAJOR, '关联交易'),
    '001002007009':    (MAJOR, '员工持股计划'),
    '001002008':       (MAJOR, '其他公司大事'),

    # ── ROUTINE：仅列表 ──
    '001001001':       (ROUTINE, '定期报告'),
    '001001002':       (ROUTINE, '定期报告(英文)'),
    '001002003':       (ROUTINE, '股东大会'),
    '001002009':       (ROUTINE, '董事会决议'),
    '001002010':       (ROUTINE, '监事会决议'),
    '001003001':       (ROUTINE, '独立董事/公司章程'),
    '001003002':       (ROUTINE, '中介机构意见'),
    '001003003':       (ROUTINE, '管理办法/制度'),
    '050003':          (ROUTINE, '调研活动'),
}

# 标题关键词补充（column_code无法覆盖时用关键词兜底）
TITLE_CRITICAL_KW = [
    '重大资产重组', '重组预案', '重组报告书', '重组实施', '重组终止',
    '收购报告书', '要约收购', '收购完成',
    '权益变动报告书', '简式权益变动', '详式权益变动',
    '重大合同', '战略合作协议', '框架协议',
    '重大诉讼', '重大仲裁', '行政处罚', '立案调查',
    '非标审计', '保留意见', '无法表示意见', '否定意见',
    '退市风险', '*ST', 'ST',
    '实际控制人变更', '控股股东变更',
    '发行股份', '非公开发行', '配股说明书',
]
TITLE_MAJOR_KW = [
    '业绩预告', '业绩快报', '业绩修正',
    '股权激励', '限制性股票', '股票期权',
    '增持计划', '增持进展', '增持结果', '增持完成',
    '减持计划', '减持进展', '减持结果',
    '回购预案', '回购方案', '回购报告书', '回购进展', '回购实施', '回购完成',
    '对外投资', '设立子公司', '投资设立',
    '利润分配', '分红', '派息',
    '担保', '质押', '冻结',
    '关联交易', '日常关联交易',
    '募集资金', '超募资金',
    '高管辞职', '董事长辞职', '总经理辞职',
    '借贷', '银行授信',
    '诉讼', '仲裁',
]


def classify_importance(title, column_codes):
    """
    基于column_code + 标题关键词 判断公告重要性
    
    Args:
        title: 公告标题
        column_codes: list of column_code strings
    
    Returns:
        (level, tag): level=CRITICAL/MAJOR/ROUTINE, tag=类型标签
    """
    # 1. 优先用 column_code 精确匹配（最长前缀匹配）
    best_match = None
    best_len = 0
    for code in column_codes:
        for prefix, (level, tag) in COLUMN_CODE_MAP.items():
            if code.startswith(prefix) and len(prefix) > best_len:
                best_match = (level, tag)
                best_len = len(prefix)
    
    if best_match:
        return best_match
    
    # 2. 标题关键词兜底
    for kw in TITLE_CRITICAL_KW:
        if kw in title:
            return (CRITICAL, f'关键词匹配({kw})')
    for kw in TITLE_MAJOR_KW:
        if kw in title:
            return (MAJOR, f'关键词匹配({kw})')
    
    return (ROUTINE, '一般公告')


# ============================================================
# 二、事件溯源：追溯关联历史公告
# ============================================================

# 需要溯源的事件类型及其追溯关键词
TRACE_CONFIGS = {
    '重大资产重组': {
        'trace_keywords': ['重组预案', '重组报告书', '重组进展', '重组实施', '重组完成', '重组终止',
                          '资产重组', '重大资产出售', '重大资产购买', '重大资产置换'],
        'max_months': 36,  # 最多追溯36个月
        'min_count': 3,    # 至少追溯3条关联公告
    },
    '收购/出售资产': {
        'trace_keywords': ['收购', '出售', '剥离', '置入', '置出', '并购'],
        'max_months': 24,
        'min_count': 3,
    },
    '重大合同': {
        'trace_keywords': ['合同', '协议', '合作', '框架', '采购'],
        'max_months': 12,
        'min_count': 2,
    },
    '诉讼仲裁': {
        'trace_keywords': ['重大诉讼', '重大仲裁', '诉讼公告', '仲裁公告', '判决', '裁定', '执行裁定', '应诉'],
        'max_months': 24,
        'min_count': 3,
    },
    '股权激励计划': {
        'trace_keywords': ['股权激励', '限制性股票', '股票期权', '激励计划', '激励对象'],
        'max_months': 18,
        'min_count': 3,
    },
    '股份增减持': {
        'trace_keywords': ['增持', '减持', '大宗交易', '协议转让'],
        'max_months': 12,
        'min_count': 2,
    },
    '回购': {
        'trace_keywords': ['回购预案', '回购方案', '回购报告书', '回购进展', '回购实施', '回购完成'],
        'max_months': 18,
        'min_count': 3,
    },
    '关联交易': {
        'trace_keywords': ['关联交易', '日常关联', '关联方'],
        'max_months': 12,
        'min_count': 2,
    },
    '募集资金': {
        'trace_keywords': ['募集资金', '超募资金', '专项说明'],
        'max_months': 18,
        'min_count': 2,
    },
    '实际控制人变更': {
        'trace_keywords': ['实际控制人', '控股股东变更', '继承', '过户', '控制权变更'],
        'max_months': 24,
        'min_count': 3,
    },
    '权益变动报告书': {
        'trace_keywords': ['权益变动', '简式权益变动', '详式权益变动', '协议转让', '大宗交易', '继承', '过户', '增持计划', '减持计划'],
        'max_months': 18,
        'min_count': 3,
    },
}


def trace_event_chain(event_tag, all_announcements, event_date_str, max_months=36):
    """
    事件溯源：从全量公告中追溯与指定事件相关的历史公告链
    
    Args:
        event_tag: 事件类型标签（如'重大资产重组'）
        all_announcements: 全量公告列表（已按日期倒序排列）
        event_date_str: 事件日期字符串 'YYYY-MM-DD'
        max_months: 最大回溯月数
    
    Returns:
        dict: {
            'chain': [...],       # 关联公告链（按时间正序）
            'origin': {...},      # 最初源头公告
            'timeline': str,      # 时间线摘要
        }
    """
    config = TRACE_CONFIGS.get(event_tag)
    if not config:
        return {'chain': [], 'origin': None, 'timeline': ''}
    
    trace_kws = config['trace_keywords']
    max_months = min(max_months, config['max_months'])
    min_count = config['min_count']
    
    try:
        event_date = datetime.strptime(event_date_str[:10], '%Y-%m-%d')
    except:
        event_date = datetime.now()
    
    cutoff_date = event_date - timedelta(days=max_months * 30)
    
    chain = []
    for ann in all_announcements:
        ann_date_str = ann.get('date', '')[:10]
        if not ann_date_str:
            continue
        try:
            ann_date = datetime.strptime(ann_date_str, '%Y-%m-%d')
        except:
            continue
        
        # 不超过最大回溯期
        if ann_date < cutoff_date:
            continue
        
        # 跳过自身（同一天同标题）
        if ann_date_str == event_date_str[:10] and ann.get('title','') == '':
            continue
        
        title = ann.get('title', '')
        # 同一天的公告也检查（比如收购报告书+法律意见书同天发布）
        if any(kw in title for kw in trace_kws):
            chain.append(ann)
    
    # 按时间正序排列（最早的在前）
    chain.sort(key=lambda x: x.get('date', ''))
    
    # 宁缺毋滥：不强制填充无关公告，保留真实关联性
    
    # 找源头（最早的关联公告）
    origin = chain[0] if chain else None
    
    # 生成时间线摘要
    timeline_parts = []
    for a in chain:
        d = a.get('date', '')[:10]
        t = a.get('title', '')[:50]
        timeline_parts.append(f"[{d}] {t}")
    if origin:
        timeline_parts.insert(0, f"溯源起点: [{origin.get('date','')[:10]}] {origin.get('title','')[:50]}")
    
    return {
        'chain': chain,
        'origin': origin,
        'timeline': '\n'.join(timeline_parts),
        'chain_length': len(chain),
    }


# ============================================================
# 三、PDF下载 + 关键内容提取
# ============================================================

def extract_ann_text_via_browser(stock_code, art_code, max_retries=2):
    """
    通过xbrowser打开公告详情页，提取正文文本。
    东方财富详情页直接渲染了完整公告内容，比PDF下载更可靠。
    
    Returns:
        str: 公告正文文本，失败返回None
    """
    # 检测可用浏览器：优先edge（稳定），其次chrome，最后cft
    _browsers_to_try = ['edge', 'chrome', 'cft']
    _browser = 'cft'  # 默认
    XB_SCRIPT = os.path.join(
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        'QClaw', 'resources', 'openclaw', 'config', 'skills',
        'xbrowser', 'scripts', 'xb.cjs'
    )
    if not os.path.exists(XB_SCRIPT):
        return None
    # 检查浏览器安装状态
    try:
        r0 = subprocess.run(['node', XB_SCRIPT, 'status'], capture_output=True, text=True, encoding='utf-8', timeout=10)
        status_data = json.loads(r0.stdout)
        browsers_info = status_data.get('data', {}).get('browsers', {})
        for b in _browsers_to_try:
            if browsers_info.get(b, {}).get('installed'):
                _browser = b
                break
    except Exception:
        pass
    
    detail_url = f'https://data.eastmoney.com/notices/detail/{stock_code}/{art_code}.html'
    
    for attempt in range(max_retries):
        try:
            # 1. 打开公告详情页
            r1 = subprocess.run(
                ['node', XB_SCRIPT, 'run', '--browser', _browser, 'open', detail_url],
                capture_output=True, text=True, encoding='utf-8', timeout=25
            )
            data1 = json.loads(r1.stdout)
            if not data1.get('ok'):
                continue
            title = data1.get('data',{}).get('result',{}).get('data',{}).get('title','')
            if not title:
                continue
            
            time.sleep(1.5)  # 等页面渲染
            
            # 2. 提取正文：去掉导航/侧栏，只取公告内容区
            js_extract = (
                '(function() {'
                'var main = document.querySelector(".detail-content")'
                ' || document.querySelector(".newsContent")'
                ' || document.querySelector("#ContentBody")'
                ' || document.querySelector(".main-body");'
                'if (main) return main.innerText;'
                'var full = document.body.innerText;'
                'var idx = full.indexOf("公告正文");'
                'if (idx > 0) return full.slice(idx);'
                'idx = full.indexOf("公告编号");'
                'if (idx > 0) return full.slice(idx);'
                'return full;'
                '})()'
            )
            
            r2 = subprocess.run(
                ['node', XB_SCRIPT, 'run', '--browser', _browser, 'eval', js_extract],
                capture_output=True, text=True, encoding='utf-8', timeout=15
            )
            data2 = json.loads(r2.stdout)
            if not data2.get('ok'):
                continue
            # JSON路径: data.result.data.result (xb CLI包装)
            result_obj = data2.get('data',{}).get('result',{})
            if isinstance(result_obj, dict):
                text = result_obj.get('data', {}).get('result', '')
                if not text:
                    # 兼容：有时只有 data.result.result
                    text = result_obj.get('result', '')
            elif isinstance(result_obj, str):
                text = result_obj
            else:
                text = ''
            if text and len(str(text)) > 200:
                raw = str(text)
                # 裁剪噪声：网友评论、页脚等
                noise_markers = ['网友评论', '郑重声明', '全部评论', '加载更多', '查看全部评论']
                for marker in noise_markers:
                    cut = raw.find(marker)
                    if cut > 200:  # 至少保留200字正文
                        raw = raw[:cut]
                        break
                return raw
        except Exception as e:
            print(f'  [xbrowser提取] 第{attempt+1}次失败: {e}')
            time.sleep(2)
    
    return None


def download_announcement_pdf(ann_info, dest_dir, market='a'):
    """
    下载公告PDF（兼容新旧art_code格式）
    ann_info: dict with art_code (A股) or announcement_id+adjunct_url (港股)
    
    新格式art_code: AN202604161821271212 → PDF在pdf.dfcfw.com
    旧格式art_code: 纯数字 → PDF在reportimages.eastmoney.com
    """
    os.makedirs(dest_dir, exist_ok=True)

    if market == 'a':
        art_code = ann_info.get('art_code', '')
        if not art_code or len(art_code) < 10:
            return None
        
        # 新格式：AN开头 → pdf.dfcfw.com
        if art_code.startswith('AN'):
            pdf_url = f'https://pdf.dfcfw.com/pdf/H2_{art_code}_1.pdf'
            try:
                r = requests.get(pdf_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': f'https://data.eastmoney.com/notices/detail/{ann_info.get("stock_code","")}/{art_code}.html',
                }, timeout=20)
                if r.status_code == 200 and r.content[:4] == b'%PDF' and len(r.content) > 5000:
                    dest = os.path.join(dest_dir, f"{art_code}.pdf")
                    with open(dest, 'wb') as f:
                        f.write(r.content)
                    return dest
            except Exception:
                pass
            # PDF下载失败（JS反爬），返回None，由调用方走xbrowser文本提取
            return None
        
        # 旧格式：纯数字 → reportimages
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
                    dest = os.path.join(dest_dir, f"{art_code}.pdf")
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
                dest = os.path.join(dest_dir, f"{aid}.pdf")
                with open(dest, 'wb') as f:
                    f.write(r.content)
                return dest
        except Exception:
            pass

    return None


def extract_key_content_from_text(text, event_tag):
    """
    从纯文本提取关键内容（来自xbrowser页面提取，非PDF）
    与extract_key_content复用同一套_extract_facts_by_type逻辑
    
    Returns:
        dict: {
            'full_text_preview': str,   # 前5000字预览
            'key_facts': list,          # 提取的关键事实
            'text_length': int,         # 文本长度
        }
    """
    if not text or len(text) < 50:
        return {'error': '文本内容为空或过短', 'key_facts': []}
    
    preview = text[:5000]
    facts = _extract_facts_by_type(text, event_tag)
    
    return {
        'full_text_preview': preview,
        'key_facts': facts,
        'text_length': len(text),
        'source': 'xbrowser_page_text',
    }


def extract_key_content(pdf_path, event_tag, max_pages=20):
    """
    从PDF提取关键内容（根据事件类型提取不同章节）
    
    Args:
        pdf_path: PDF文件路径
        event_tag: 事件类型标签
        max_pages: 最多读取页数
    
    Returns:
        dict: {
            'full_text_preview': str,   # 前5000字预览
            'key_facts': list,          # 提取的关键事实
            'page_count': int,          # 总页数
        }
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {'error': 'PyMuPDF未安装，无法提取PDF内容'}
    
    if not os.path.exists(pdf_path):
        return {'error': f'PDF文件不存在: {pdf_path}'}
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return {'error': f'打开PDF失败: {e}'}
    
    page_count = len(doc)
    read_pages = min(page_count, max_pages)
    
    text = ''
    for i in range(read_pages):
        text += doc[i].get_text('text')
    doc.close()
    
    # 提取关键事实（根据事件类型）
    key_facts = _extract_facts_by_type(text, event_tag)
    
    return {
        'full_text_preview': text[:5000],
        'key_facts': key_facts,
        'page_count': page_count,
        'read_pages': read_pages,
    }


def _extract_facts_by_type(text, event_tag):
    """根据事件类型从文本中提取关键事实"""
    facts = []
    
    # 通用提取：金额（优先带币种/单位的精确匹配）
    amount_patterns = [
        r'(?:人民币|RMBC?[：:\s]*)([\d,.]+)\s*亿元',
        r'(?:人民币|RMBC?[：:\s]*)([\d,.]+)\s*万元',
        r'([\d,.]+)\s*亿美元',
        r'([\d,.]+)\s*万美元',
        r'([\d,.]+)\s*美元',
        r'([\d,.]+)\s*亿元',
        r'([\d,.]+)\s*万元',
        r'(?:金额|总金额|对价|交易价格|合同金额|主张金额)[：:\s]*([\d,.，、]+\s*[万亿]?[美]?元)',
    ]
    for pat in amount_patterns:
        matches = re.findall(pat, text[:8000])
        if matches:
            # 如果正则已含单位，直接用；否则标注为元
            m = matches[0]
            if '美元' in pat or '亿' in pat or '万' in pat:
                unit = '亿美元' if '亿美元' in pat else ('万美元' if '万美元' in pat else ('美元' if '美元' in pat else ('亿元' if '亿元' in pat else '万元')))
                facts.append(f"涉及金额: {m}{unit}")
            else:
                facts.append(f"涉及金额: {m}")
            break
    
    if '重组' in event_tag or '收购' in event_tag or '出售' in event_tag:
        # 重组/收购类：提取交易对方、标的、对价
        counterparty = re.search(r'交易对方[：:]\s*([^\n]{2,50})', text)
        if counterparty:
            facts.append(f"交易对方: {counterparty.group(1).strip()}")
        target = re.search(r'标的[公司资产]*[：:]\s*([^\n]{2,50})', text)
        if target:
            facts.append(f"交易标的: {target.group(1).strip()}")
        price = re.search(r'交易[对价价格金额][：:]\s*([^\n]{2,50})', text)
        if price:
            facts.append(f"交易对价: {price.group(1).strip()}")
    
    elif '合同' in event_tag:
        # 合同类：提取合同双方、标的、金额、期限
        party_a = re.search(r'甲方[：:]\s*([^\n]{2,50})', text)
        if party_a:
            facts.append(f"甲方: {party_a.group(1).strip()}")
        party_b = re.search(r'乙方[：:]\s*([^\n]{2,50})', text)
        if party_b:
            facts.append(f"乙方: {party_b.group(1).strip()}")
        contract_amt = re.search(r'合同[总金][额价][：:]\s*([^\n]{2,50})', text)
        if contract_amt:
            facts.append(f"合同金额: {contract_amt.group(1).strip()}")
    
    elif '诉讼' in event_tag or '仲裁' in event_tag:
        # 诉讼类：提取原告、被告、诉求、涉案金额、受理法院、判决结果
        plaintiff = re.search(r'(?:^|\n)\s*原告[：:]\s*([^\n，。]{2,80})', text[:8000])
        if plaintiff:
            facts.append(f"原告: {plaintiff.group(1).strip()}")
        defendant = re.search(r'被告[：:\s]*([\s\S]{2,200}?)(?:的(?:股东|侵权|诉讼|合同|重大)|\n\n|。|；)', text[:8000])
        if defendant:
            facts.append(f"被告: {defendant.group(1).strip()}")
        claim = re.search(r'(?:诉讼请求|仲裁请求|请求事项)[：:\s]*([\s\S]{5,600}?)(?:\n\s*\n\s*(?:（|\d+[、.]))', text[:8000])
        if claim:
            facts.append(f"诉求: {claim.group(1).strip()}")
        court = re.search(r'(?:受理|管辖)法院[：:\s]*([^\n，。]{2,50})', text[:8000])
        if court:
            facts.append(f"受理法院: {court.group(1).strip()}")
        ruling = re.search(r'(?:判决|裁定|裁决|调解)[结果书][：:\s]*([^\n]{5,200})', text[:8000])
        if ruling:
            facts.append(f"判决/裁决: {ruling.group(1).strip()}")
        # 诉讼金额（更宽泛匹配，含美元）
        suit_amt = re.search(r'(?:主张|诉请|请求).*?(?:金额|数额|赔偿)[约为不超过]*\s*([\d,.，]+\s*[万亿]?[美]?元)', text[:8000])
        if suit_amt:
            facts.append(f"诉请金额: {suit_amt.group(1).strip()}")
        elif not any('涉及金额' in f for f in facts):
            # 退而求其次，找大额美元数字
            usd_match = re.search(r'([\d,.]+)\s*美元', text[:8000])
            if usd_match:
                facts.append(f"涉案金额: {usd_match.group(1)}美元")
    
    elif '激励' in event_tag:
        # 股权激励类：提取激励数量、行权价、对象
        qty = re.search(r'(?:授予|拟授予|拟激励).*?(\d[\d,.]*\s*万?股)', text[:3000])
        if qty:
            facts.append(f"激励数量: {qty.group(1)}")
        price = re.search(r'(?:行权价格|授予价格)[：:]\s*([\d.]+\s*元?/股)', text[:5000])
        if price:
            facts.append(f"行权/授予价格: {price.group(1)}")
    
    elif '回购' in event_tag:
        # 回购类：提取回购金额、价格区间、用途
        amt = re.search(r'回购[资金金额总][额价][：:不超过]*\s*([\d,.]+\s*万?亿?元)', text[:3000])
        if amt:
            facts.append(f"回购金额: {amt.group(1)}")
        price_range = re.search(r'回购价格[区间不超过]*[：:]\s*([\d.\-～~]+\s*元?/股)', text[:3000])
        if price_range:
            facts.append(f"回购价格: {price_range.group(1)}")
    
    # 通用：提取日期
    date_patterns = [
        r'(?:签署日期|签订日期|生效日期|审议通过日期)[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
    ]
    for pat in date_patterns:
        m = re.search(pat, text[:5000])
        if m:
            facts.append(f"关键日期: {m.group(1)}")
            break
    
    return facts


# ============================================================
# 四、主采集函数
# ============================================================

def fetch_announcements(stock_code, market='a', data_dir=None,
                        deep_extract=True, max_critical=5, trace_events=True):
    """
    获取并分类整理A股/港股公告（增强版）
    
    Args:
        stock_code: 股票代码
        market: 'a' 或 'hk'
        data_dir: 数据目录（用于保存PDF）
        deep_extract: 是否对CRITICAL公告自动下载PDF+提取内容
        max_critical: 最多深挖的CRITICAL公告数量
        trace_events: 是否对重要事件进行溯源
    
    Returns:
        {
            count,                    # 总公告数
            importance_stats,         # 分级统计
            critical_announcements,   # 🔴 CRITICAL公告列表（含提取内容）
            major_announcements,      # 🟡 MAJOR公告列表
            routine_announcements,    # 🟢 ROUTINE公告列表
            event_chains,             # 事件溯源链
            categories,               # 按栏目分类
            recent_30,                # 近30条
            metadata,
            _meta,
        }
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

    # ---- 分级分类 ----
    critical_list = []
    major_list = []
    routine_list = []
    
    for ann in all_anns:
        col_codes = ann.get('column_codes', [])
        title = ann.get('title', '')
        level, tag = classify_importance(title, col_codes)
        ann['importance'] = level
        ann['importance_tag'] = tag
        
        if level == CRITICAL:
            critical_list.append(ann)
        elif level == MAJOR:
            major_list.append(ann)
        else:
            routine_list.append(ann)
    
    # ---- CRITICAL公告深挖：xbrowser文本提取 > PDF下载 ----
    if deep_extract and data_dir and critical_list:
        pdf_dir = os.path.join(data_dir, 'critical_announcements')
        extracted_count = 0
        for ann in critical_list[:max_critical]:
            try:
                art_code = ann.get('art_code', '')
                content = None
                
                # 优先方案：xbrowser提取详情页正文（更快、抗反爬）
                if market == 'a' and art_code:
                    text = extract_ann_text_via_browser(stock_code, art_code)
                    if text:
                        content = extract_key_content_from_text(
                            text, ann.get('importance_tag', '')
                        )
                        ann['extract_method'] = 'xbrowser'
                        ann['detail_url'] = f'https://data.eastmoney.com/notices/detail/{stock_code}/{art_code}.html'
                
                # 备选方案：下载PDF + PyMuPDF提取
                if not content:
                    pdf_path = download_announcement_pdf(ann, pdf_dir, market=market)
                    if pdf_path:
                        content = extract_key_content(pdf_path, ann.get('importance_tag', ''))
                        ann['pdf_path'] = pdf_path
                        ann['extract_method'] = 'pdf'
                
                if content:
                    ann['extracted_content'] = content
                    extracted_count += 1
                    print(f"  [深挖] {ann.get('date','')[:10]} {ann.get('title','')[:50]} → {content.get('key_facts', [])}")
                else:
                    ann['extracted_content'] = {'error': '文本提取失败（xbrowser+PDF均不可用）'}
            except Exception as e:
                ann['extracted_content'] = {'error': str(e)}
        
        steps.append({
            'step': 'deep_extract',
            'label': 'CRITICAL公告深挖',
            'source': 'xbrowser + pdf_fallback',
            'count': extracted_count,
            'status': 'OK' if extracted_count > 0 else 'SKIP',
        })
    
    # ---- 事件溯源 ----
    event_chains = {}
    if trace_events and critical_list:
        # 对每种CRITICAL事件类型做溯源
        traced_tags = set()
        for ann in critical_list:
            tag = ann.get('importance_tag', '')
            if tag in traced_tags:
                continue
            traced_tags.add(tag)
            
            chain_result = trace_event_chain(
                tag, all_anns, ann.get('date', '')
            )
            if chain_result['chain']:
                event_chains[tag] = chain_result
                print(f"  [溯源] {tag}: 追溯到{chain_result['chain_length']}条关联公告")
        
        if event_chains:
            steps.append({
                'step': 'trace_events',
                'label': '事件溯源',
                'source': 'em_announce',
                'count': sum(c['chain_length'] for c in event_chains.values()),
                'status': 'OK',
            })
    
    # 分类（兼容旧接口）
    categories = _categorize(all_anns)
    recent_30 = all_anns[:30]
    
    # 兼容旧 key_events
    key_events = [a for a in all_anns if a.get('importance') in (CRITICAL, MAJOR)][:20]

    # 统计
    importance_stats = {
        'critical': len(critical_list),
        'major': len(major_list),
        'routine': len(routine_list),
    }

    # 溯源
    ok_step = next((s for s in steps if s['status'] == 'OK'), None)
    top_source = ok_step['source'] if ok_step else ('em_announce' if market == 'a' else 'cninfo_hk_announce')

    return {
        'count': len(all_anns),
        'importance_stats': importance_stats,
        'critical_announcements': critical_list,
        'major_announcements': major_list,
        'routine_announcements': routine_list,
        'event_chains': event_chains,
        'categories': categories,
        'recent_30': recent_30,
        'key_events': key_events,  # 兼容旧接口
        'metadata': {
            'total_fetched': len(all_anns),
            'date_range': (
                all_anns[-1]['date'] if all_anns else None,
                all_anns[0]['date'] if all_anns else None,
            ),
            'deep_extracted': sum(1 for a in critical_list if a.get('extracted_content')),
            'event_chains_count': len(event_chains),
        },
        '_meta': {
            'source': top_source,
            'steps': steps,
            'fetched_at': _dt.now().isoformat(),
        },
    }


# ============================================================
# 五、底层获取函数
# ============================================================

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
        columns = item.get('columns', [])
        col_str = '|'.join(c.get('column_name', '') for c in columns)
        col_codes = [c.get('column_code', '') for c in columns if c.get('column_code')]

        result.append({
            'date': notice_date,
            'title': title,
            'art_code': art_code,
            'category': col_str,
            'column_codes': col_codes,  # 新增：保留完整column_code
            'source': '东方财富',
            'stock_code': stock_code,
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
        
        # 港股也做重要性分类（用关键词，因为没有column_code）
        level, tag = _classify_hk_importance(title)
        
        result.append({
            'date': pub_date,
            'title': title,
            'announcement_id': aid,
            'adjunct_url': adjunct_url,
            'source': 'CNINFO港股',
            'stock_code': stock_code,
            'importance': level,
            'importance_tag': tag,
        })
    return result


def _classify_hk_importance(title):
    """港股公告重要性分类（基于标题关键词）"""
    critical_kw = [
        '要约收购', '私有化', '非常重大', '重大出售', '重大收购',
        '主要交易', '须予披露', '反收购', '红利股',
    ]
    major_kw = [
        '业绩', '盈利警告', '盈利预告', '董事', '主席', 'CEO',
        '回购', '增持', '减持', '配售', '供股',
        '股息', '特别股息', '分红',
        '关联交易', '关连交易',
        '诉讼', '仲裁', '监管',
    ]
    
    for kw in critical_kw:
        if kw in title:
            return (CRITICAL, f'港股关键词({kw})')
    for kw in major_kw:
        if kw in title:
            return (MAJOR, f'港股关键词({kw})')
    return (ROUTINE, '港股一般公告')


def _categorize(anns):
    """按来源+栏目分类"""
    categories = {}
    for a in anns:
        cat = a.get('category', a.get('source', '其他'))
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(a)
    return categories


if __name__ == '__main__':
    result = fetch_announcements('002180', 'a', data_dir='./output')
    print(f"\n获取 {result['count']} 条公告")
    print(f"分级统计: {result['importance_stats']}")
    
    print(f"\n{'='*60}")
    print(f"  🔴 CRITICAL ({result['importance_stats']['critical']}条)")
    print(f"{'='*60}")
    for a in result['critical_announcements'][:5]:
        facts = a.get('extracted_content', {}).get('key_facts', [])
        fact_str = ' | '.join(facts) if facts else ''
        print(f"  {a.get('date','')[:10]} | {a.get('importance_tag','')} | {a.get('title','')[:60]}")
        if fact_str:
            print(f"         关键事实: {fact_str}")
    
    print(f"\n{'='*60}")
    print(f"  🟡 MAJOR ({result['importance_stats']['major']}条)")
    print(f"{'='*60}")
    for a in result['major_announcements'][:5]:
        print(f"  {a.get('date','')[:10]} | {a.get('importance_tag','')} | {a.get('title','')[:60]}")
    
    print(f"\n{'='*60}")
    print(f"  🟢 ROUTINE ({result['importance_stats']['routine']}条)")
    print(f"{'='*60}")
    print(f"  ... (仅列表)")
    
    if result.get('event_chains'):
        print(f"\n{'='*60}")
        print(f"  📎 事件溯源链")
        print(f"{'='*60}")
        for tag, chain in result['event_chains'].items():
            print(f"  [{tag}] 追溯{chain['chain_length']}条:")
            print(f"  {chain['timeline'][:200]}")
