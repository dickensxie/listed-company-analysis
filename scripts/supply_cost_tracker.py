# -*- coding: utf-8 -*-
"""
通用全球供应链成本追踪模块
支持任意行业/公司，追踪关键原材料/零部件价格趋势

数据源：
1. 上海有色金属网 (SMM) - 铜、铝、锂等
2. 公开大宗商品API - 伦敦金属交易所(LME)等
3. 行业公开报价 - DRAMeXchange等效数据源
4. 新闻抓取 - 价格变动新闻

用法:
    python supply_cost_tracker.py --industry "消费电子"
    python supply_cost_tracker.py --company "小米集团" --industry "消费电子"
    python supply_cost_tracker.py --components "DRAM,NAND,锂电池"
"""
import sys, os, json, re, requests, argparse, time
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

try:
    from scripts.safe_request import safe_get, safe_extract
except ImportError:
    def safe_get(url, params=None, headers=None, timeout=15, retries=2, backoff=1):
        for attempt in range(retries + 1):
            try:
                r = requests.get(url, params=params, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    try:
                        return r.json()
                    except:
                        return r.text
            except:
                if attempt < retries:
                    time.sleep(backoff * (attempt + 1))
        return None

    def safe_extract(data, keys, default=None):
        curr = data
        for k in keys:
            if isinstance(curr, dict):
                curr = curr.get(k)
            else:
                return default
        return curr if curr is not None else default


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/html, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 行业 → 关键组件映射
INDUSTRY_COMPONENTS = {
    "消费电子": {
        "DRAM": {"unit": "美元/GB", "impact": "手机/平板内存成本"},
        "NAND": {"unit": "美元/GB", "impact": "手机存储成本"},
        "OLED面板": {"unit": "美元/片", "impact": "手机屏幕成本"},
        "锂电池": {"unit": "元/Wh", "impact": "手机电池成本"},
        "铜": {"unit": "元/吨", "impact": "连接器/PCB成本"},
        "铝": {"unit": "元/吨", "impact": "外壳/散热成本"},
    },
    "新能源汽车": {
        "动力电池": {"unit": "元/Wh", "impact": "整车电池包成本"},
        "锂": {"unit": "元/吨", "impact": "正极材料成本"},
        "钴": {"unit": "元/吨", "impact": "三元材料成本"},
        "镍": {"unit": "元/吨", "impact": "高镍正极成本"},
        "铜": {"unit": "元/吨", "impact": "电机/线束成本"},
        "铝": {"unit": "元/吨", "impact": "车身/电池壳成本"},
    },
    "半导体": {
        "硅片": {"unit": "美元/片", "impact": "晶圆成本"},
        "光刻胶": {"unit": "美元/升", "impact": "光刻工艺成本"},
        "电子气体": {"unit": "元/立方米", "impact": "刻蚀/沉积成本"},
        "铜": {"unit": "元/吨", "impact": "互连材料成本"},
    },
    "光伏": {
        "多晶硅": {"unit": "元/千克", "impact": "硅片成本"},
        "银浆": {"unit": "元/千克", "impact": "电池片电极成本"},
        "光伏玻璃": {"unit": "元/平方米", "impact": "组件封装成本"},
    },
}

# 组件 → 公开数据源映射
COMPONENT_DATA_SOURCES = {
    "DRAM": [
        {"name": "DRAMeXchange等效", "url": "https://www.dramexchange.com/", "note": "需浏览器访问"},
        {"name": "搜索参考", "url": "https://www.google.com/search?q=DRAM+price+trend+2026", "note": "搜索最新报价"},
    ],
    "NAND": [
        {"name": "DRAMeXchange等效", "url": "https://www.dramexchange.com/", "note": "需浏览器访问"},
        {"name": "搜索参考", "url": "https://www.google.com/search?q=NAND+flash+price+2026", "note": "搜索最新报价"},
    ],
    "锂电池": [
        {"name": "上海有色金属网", "url": "https://www.smm.cn/", "note": "现货报价"},
        {"name": "百川盈孚", "url": "https://www.baiinfo.com/", "note": "行业报价"},
    ],
    "锂": [
        {"name": "上海有色金属网", "url": "https://www.smm.cn/price/10002", "note": "碳酸锂/氢氧化锂"},
        {"name": "Wind数据", "url": "https://www.wind.com.cn/", "note": "需订阅"},
    ],
    "铜": [
        {"name": "LME伦敦金属交易所", "url": "https://www.lme.com/en/Metals/Non-ferrous/Copper", "note": "期货价格"},
        {"name": "上海期货交易所", "url": "https://www.shfe.com.cn/", "note": "沪铜期货"},
    ],
    "铝": [
        {"name": "LME伦敦金属交易所", "url": "https://www.lme.com/en/Metals/Non-ferrous/Aluminium", "note": "期货价格"},
        {"name": "上海期货交易所", "url": "https://www.shfe.com.cn/", "note": "沪铝期货"},
    ],
    "OLED面板": [
        {"name": "WitsView", "url": "https://www.witsview.com/", "note": "面板报价"},
        {"name": "搜索参考", "url": "https://www.google.com/search?q=OLED+panel+price+trend", "note": "搜索最新报价"},
    ],
}


def get_components_for_industry(industry, custom_components=None):
    """获取行业关键组件列表"""
    components = {}

    # 先匹配行业
    for ind_key, comps in INDUSTRY_COMPONENTS.items():
        if ind_key in industry or industry in ind_key:
            components.update(comps)

    # 自定义组件补充
    if custom_components:
        for comp in custom_components.split(','):
            comp = comp.strip()
            if comp and comp not in components:
                components[comp] = {"unit": "元/单位", "impact": "成本影响"}

    return components


def search_component_price_news(component_name, days=90):
    """搜索组件价格新闻"""
    print(f"  → 搜索 {component_name} 价格新闻...")
    results = {
        'component': component_name,
        'news': [],
        'price_mentions': [],
    }

    try:
        # 使用东方财富新闻接口搜索
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        url = "https://np-listapi.eastmoney.com/eastmoney.portal.infolist.getlist"
        params = {
            'cb': '', 'industryCode': '*', 'pageSize': 20,
            'beginTime': start_date, 'endTime': end_date,
            'keywords': f'{component_name} 价格 涨价 下跌',
        }

        data = safe_get(url, params=params, headers=HEADERS, timeout=15)
        items = safe_extract(data, ['data', 'list'], [])

        for item in items:
            title = item.get('title', '')
            # 提取价格关键词
            price_keywords = ['涨价', '跌价', '上调', '下调', '上涨', '下跌', '高位', '低位', '元/吨', '元/片']
            if any(kw in title for kw in price_keywords):
                results['news'].append({
                    'date': item.get('publishTime', '')[:10],
                    'title': title,
                    'summary': item.get('summary', '')[:150],
                    'source': '东方财富新闻',
                })

        # 搜索价格数字（简单正则）
        for news in results['news']:
            summary = news.get('summary', '')
            # 匹配价格模式：数字+元/单位
            prices = re.findall(r'(\d+\.?\d*)\s*元/[吨片千WhGB]', summary)
            if prices:
                results['price_mentions'].extend(prices)

    except Exception as e:
        print(f"    新闻搜索失败: {e}")

    return results


def estimate_cost_impact(company_name, industry, component_prices):
    """
    估算成本变动对公司毛利率的影响
    简化模型：基于行业平均成本结构
    """
    print(f"  → 估算成本变动对 {company_name} 毛利率影响...")

    # 行业成本结构（简化，实际应从年报提取）
    COST_STRUCTURE = {
        "消费电子": {
            "DRAM": 0.08,    # 占营收8%
            "NAND": 0.06,    # 占营收6%
            "OLED面板": 0.15, # 占营收15%
            "锂电池": 0.03,  # 占营收3%
            "其他": 0.68,
        },
        "新能源汽车": {
            "动力电池": 0.35,
            "锂": 0.08,
            "钴": 0.05,
            "镍": 0.04,
            "铜": 0.03,
            "铝": 0.04,
            "其他": 0.41,
        },
    }

    industry_cost = COST_STRUCTURE.get(industry, {})
    if not industry_cost:
        return {
            'company': company_name,
            'industry': industry,
            'impact': '无法估算（未知行业成本结构）',
            'details': {},
        }

    impact_details = {}
    total_margin_impact = 0

    for component, price_data in component_prices.items():
        cost_weight = industry_cost.get(component, 0)
        if cost_weight == 0:
            continue

        # 模拟价格变动（实际应从数据源获取）
        # 这里用新闻中提到的变动幅度
        price_change_pct = 0
        news_count = len(price_data.get('news', []))
        if news_count > 0:
            # 简单判断：有涨价新闻 → 假设+10%，有跌价新闻 → 假设-5%
            has_price_news = any('涨价' in n.get('title', '') or '上涨' in n.get('title', '') for n in price_data['news'])
            has_down_news = any('跌价' in n.get('title', '') or '下跌' in n.get('title', '') for n in price_data['news'])
            if has_price_news:
                price_change_pct = 0.10
            elif has_down_news:
                price_change_pct = -0.05

        margin_impact = cost_weight * price_change_pct
        total_margin_impact += margin_impact

        impact_details[component] = {
            'cost_weight_pct': cost_weight * 100,
            'price_change_pct': price_change_pct * 100,
            'margin_impact_pct': margin_impact * 100,
            'news_count': news_count,
        }

    return {
        'company': company_name,
        'industry': industry,
        'total_margin_impact_pct': round(total_margin_impact * 100, 2),
        'impact_level': '高' if abs(total_margin_impact) > 0.05 else ('中' if abs(total_margin_impact) > 0.02 else '低'),
        'details': impact_details,
        'note': '基于行业平均成本结构估算，实际影响需结合公司具体采购策略',
    }


def generate_supply_cost_report(company_name=None, industry="消费电子", custom_components=None):
    """生成供应链成本追踪报告"""
    print(f"\n{'='*60}")
    print(f"📊 全球供应链成本追踪报告")
    if company_name:
        print(f"   公司: {company_name}")
    print(f"   行业: {industry}")
    print(f"{'='*60}\n")

    report = {
        'company': company_name,
        'industry': industry,
        'generated_at': datetime.now().isoformat(),
        'components': {},
        'cost_impact': {},
        'data_sources': {},
    }

    # 1. 获取关键组件
    components = get_components_for_industry(industry, custom_components)
    print(f"  关键组件: {', '.join(components.keys())}\n")

    # 2. 搜索每个组件的价格新闻
    for comp_name, comp_info in components.items():
        report['components'][comp_name] = {
            'info': comp_info,
            'price_news': search_component_price_news(comp_name),
            'data_sources': COMPONENT_DATA_SOURCES.get(comp_name, []),
        }

    # 3. 估算成本影响
    if company_name:
        report['cost_impact'] = estimate_cost_impact(
            company_name, industry, report['components']
        )

    # 4. 数据源汇总
    all_sources = set()
    for comp_name, sources in COMPONENT_DATA_SOURCES.items():
        if comp_name in components:
            for s in sources:
                all_sources.add(s['name'])
    report['data_sources'] = list(all_sources)

    return report


def format_markdown_report(report):
    """格式化供应链成本报告为Markdown"""
    lines = []
    lines.append("# 📊 全球供应链成本追踪报告\n")
    if report.get('company'):
        lines.append(f"**公司**: {report['company']}")
    lines.append(f"**行业**: {report['industry']}")
    lines.append(f"**生成时间**: {report['generated_at'][:19]}")
    lines.append("\n---\n")

    # 关键组件
    lines.append("## 一、关键组件清单\n")
    components = report.get('components', {})
    if components:
        lines.append("| 组件 | 单位 | 成本影响 | 数据源 |")
        lines.append("|------|------|---------|--------|")
        for comp_name, comp_data in components.items():
            info = comp_data.get('info', {})
            sources = comp_data.get('data_sources', [])
            source_names = ', '.join([s['name'] for s in sources]) if sources else '无'
            lines.append(f"| {comp_name} | {info.get('unit', '?')} | {info.get('impact', '?')} | {source_names} |")
    lines.append("")

    # 价格新闻
    lines.append("## 二、近期价格动态（近90天）\n")
    for comp_name, comp_data in components.items():
        news_data = comp_data.get('price_news', {})
        news_list = news_data.get('news', [])

        lines.append(f"### {comp_name} ({len(news_list)}条新闻)\n")
        if news_list:
            for news in news_list[:5]:
                lines.append(f"- **{news.get('date', '')}** {news.get('title', '')}")
                if news.get('summary'):
                    lines.append(f"  > {news['summary'][:100]}...")
        else:
            lines.append("_近90天未发现明显价格新闻_")
        lines.append("")

    # 成本影响估算
    cost_impact = report.get('cost_impact', {})
    if cost_impact and 'total_margin_impact_pct' in cost_impact:
        lines.append("## 三、成本变动对毛利率影响估算\n")
        impact_icon = {'高': '🔴', '中': '🟡', '低': '✅'}.get(cost_impact.get('impact_level', '低'), '❓')
        lines.append(f"**影响等级**: {impact_icon} {cost_impact.get('impact_level', '未知')}")
        lines.append(f"**毛利率影响**: {cost_impact.get('total_margin_impact_pct', 0):+.2f} 个百分点")
        lines.append(f"**估算说明**: {cost_impact.get('note', '')}")
        lines.append("")

        if cost_impact.get('details'):
            lines.append("### 分组件影响明细\n")
            lines.append("| 组件 | 成本占比 | 价格变动 | 毛利率影响 | 新闻数 |")
            lines.append("|------|---------|---------|-----------|--------|")
            for comp, detail in cost_impact['details'].items():
                lines.append(
                    f"| {comp} | {detail['cost_weight_pct']:.1f}% | "
                    f"{detail['price_change_pct']:+.1f}% | {detail['margin_impact_pct']:+.2f}% | {detail['news_count']} |"
                )
        lines.append("")

    # 数据来源
    lines.append("## 四、数据来源与查询入口\n")
    all_sources = report.get('data_sources', [])
    if all_sources:
        for src in all_sources:
            lines.append(f"- {src}")
    else:
        lines.append("_无可用数据源_")

    # 关键组件数据源
    lines.append("\n### 各组件查询入口\n")
    for comp_name, comp_data in components.items():
        sources = comp_data.get('data_sources', [])
        if sources:
            lines.append(f"**{comp_name}**:")
            for s in sources:
                lines.append(f"  - [{s['name']}]({s['url']}) — {s['note']}")
    lines.append("")

    lines.append("\n---\n")
    lines.append("> ⚠️ **数据说明**: 本模块通过公开新闻搜索监控价格动态，")
    lines.append("> 实时报价需要接入专业数据源（如SMM、LME、Wind等）。")
    lines.append("> 成本影响估算基于行业平均成本结构，仅供参考。")

    return "\n".join(lines)


def save_report(report, output_dir, identifier):
    """保存报告"""
    os.makedirs(output_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(output_dir, f"supply_cost_{identifier}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Markdown
    md = format_markdown_report(report)
    md_path = os.path.join(output_dir, f"supply_cost_{identifier}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"\n✅ 报告已保存:")
    print(f"   JSON: {json_path}")
    print(f"   Markdown: {md_path}")

    return md_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='全球供应链成本追踪（通用模块）')
    parser.add_argument('--company', help='公司名称（可选）')
    parser.add_argument('--industry', default='消费电子', help='行业名称')
    parser.add_argument('--components', help='自定义组件列表（逗号分隔）')
    parser.add_argument('--output', help='输出目录（默认: output/supply_cost/）')

    args = parser.parse_args()

    output_dir = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'output', 'supply_cost'
    )

    report = generate_supply_cost_report(
        company_name=args.company,
        industry=args.industry,
        custom_components=args.components,
    )

    save_report(report, output_dir, args.company or args.industry)

    # 打印报告
    print("\n" + format_markdown_report(report))
