# -*- coding: utf-8 -*-
"""
行业分析模块 V2 - AI驱动版
设计理念：Python提供分析框架，AI通过web_search搜集数据后灌入
彻底解决沙箱网络限制问题
"""
import sys, os, re, json, argparse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────
# 数据输入接口（AI通过web_search搜集后传入）
# ─────────────────────────────────────────────

def build_search_queries(industry_name, year=2026):
    """
    返回需要AI搜集的数据结构
    AI拿到这个结构后，用web_search逐一搜索，结果填回generate_report
    """
    return {
        "industry": industry_name,
        "year": year,
        "queries": {
            "PEST": {
                "P_政策": [
                    f"{industry_name} 最新政策法规 {year}",
                    f"{industry_name} 监管动态 政府规划",
                ],
                "E_经济": [
                    f"{industry_name} 市场规模 增长率 {year}",
                    f"{industry_name} 宏观经济影响 需求驱动",
                ],
                "S_社会": [
                    f"{industry_name} 消费群体 人口结构",
                    f"{industry_name} 消费趋势 行为变化",
                ],
                "T_技术": [
                    f"{industry_name} 技术创新 突破 {year}",
                    f"{industry_name} 研发投入 技术路线",
                ],
            },
            "波特五力": {
                "现有竞争": f"{industry_name} 主要竞争对手 市场份额 {year}",
                "新进入者": f"{industry_name} 进入壁垒 牌照 资本要求",
                "替代品": f"{industry_name} 替代品 替代技术 风险",
                "供应商议价": f"{industry_name} 供应链 供应商集中度",
                "买方议价": f"{industry_name} 客户集中度 议价能力",
            },
            "市场规模": {
                "TAM": f"{industry_name} 总潜在市场规模 TAM",
                "SAM": f"{industry_name} 可服务市场规模 SAM",
                "SOM": f"{industry_name} 可获得市场份额 SOM",
            },
            "竞品": f"{industry_name} 龙头公司 市场份额排名 {year}",
        }
    }


def generate_report(industry_name, search_results, year=2026):
    """
    根据AI搜集的数据生成完整报告
    
    参数:
        industry_name: 行业名称
        search_results: AI通过web_search搜集的数据，格式如下:
        {
            "PEST": {
                "P_政策": "政策内容...",
                "E_经济": "经济内容...",
                ...
            },
            "波特五力": {
                "现有竞争": "...",
                ...
            },
            "市场规模": {
                "TAM": "xxx亿",
                "SAM": "xxx亿",
                "SOM": "xxx亿"
            },
            "竞品": "竞品信息..."
        }
    """
    report = []
    report.append(f"# {industry_name} 行业深度研究报告")
    report.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**研究年度**: {year}")
    report.append("\n---\n")
    
    # ═════════════════════════════════════════
    # 一、PEST宏观环境分析
    # ═════════════════════════════════════════
    report.append("## 一、PEST宏观环境分析\n")
    
    pest_data = search_results.get("PEST", {})
    pest_scores = {}
    
    # P 政策
    p_content = pest_data.get("P_政策", "暂无数据")
    report.append("### 1. 政治法律环境 (Political)\n")
    report.append(p_content)
    report.append("\n")
    pest_scores["P"] = _score_dimension(p_content)
    
    # E 经济
    e_content = pest_data.get("E_经济", "暂无数据")
    report.append("### 2. 经济环境 (Economic)\n")
    report.append(e_content)
    report.append("\n")
    pest_scores["E"] = _score_dimension(e_content)
    
    # S 社会
    s_content = pest_data.get("S_社会", "暂无数据")
    report.append("### 3. 社会文化环境 (Social)\n")
    report.append(s_content)
    report.append("\n")
    pest_scores["S"] = _score_dimension(s_content)
    
    # T 技术
    t_content = pest_data.get("T_技术", "暂无数据")
    report.append("### 4. 技术环境 (Technological)\n")
    report.append(t_content)
    report.append("\n")
    pest_scores["T"] = _score_dimension(t_content)
    
    # PEST评分表
    report.append("\n#### PEST综合评分\n")
    report.append("| 维度 | 评分(1-5) | 判断 |")
    report.append("|------|-----------|------|")
    for dim, score in pest_scores.items():
        judge = "有利" if score >= 4 else "中性" if score >= 3 else "不利"
        dim_name = {"P": "政策", "E": "经济", "S": "社会", "T": "技术"}[dim]
        report.append(f"| {dim_name} | {score}/5 | {judge} |")
    
    avg_score = sum(pest_scores.values()) / len(pest_scores) if pest_scores else 3
    report.append(f"\n**综合评分**: {avg_score:.1f}/5 — {'整体环境有利' if avg_score >= 3.5 else '环境中性偏谨慎' if avg_score >= 2.5 else '环境不利，需谨慎'}\n")
    
    # ═════════════════════════════════════════
    # 二、波特五力竞争分析
    # ═════════════════════════════════════════
    report.append("\n---\n")
    report.append("## 二、波特五力竞争分析\n")
    
    porter_data = search_results.get("波特五力", {})
    
    forces = [
        ("现有竞争者竞争", "现有竞争", "高"),
        ("新进入者威胁", "新进入者", "中"),
        ("替代品威胁", "替代品", "低"),
        ("供应商议价能力", "供应商议价", "中"),
        ("买方议价能力", "买方议价", "中"),
    ]
    
    report.append("| 竞争力量 | 强度 | 关键发现 |")
    report.append("|----------|------|----------|")
    
    for force_name, key, default_intensity in forces:
        content = porter_data.get(key, "暂无数据")
        intensity = _assess_force_intensity(content) if content != "暂无数据" else default_intensity
        summary = content[:50] + "..." if len(content) > 50 else content
        report.append(f"| {force_name} | {intensity} | {summary} |")
    
    # 竞争强度判断
    high_count = sum(1 for _, key, _ in forces if _assess_force_intensity(porter_data.get(key, "")) == "高")
    if high_count >= 3:
        competition_level = "行业竞争激烈，利润空间受挤压"
    elif high_count >= 2:
        competition_level = "行业竞争中等，存在一定利润空间"
    else:
        competition_level = "行业竞争相对温和，利润空间较好"
    
    report.append(f"\n**竞争格局判断**: {competition_level}\n")
    
    # ═════════════════════════════════════════
    # 三、市场规模测算 (TAM/SAM/SOM)
    # ═════════════════════════════════════════
    report.append("\n---\n")
    report.append("## 三、市场规模测算\n")
    
    market_data = search_results.get("市场规模", {})
    
    tam = market_data.get("TAM", "未知")
    sam = market_data.get("SAM", "未知")
    som = market_data.get("SOM", "未知")
    
    report.append(f"""
| 市场层级 | 规模 | 定义 |
|----------|------|------|
| TAM (总潜在市场) | {tam} | 行业理论最大市场 |
| SAM (可服务市场) | {sam} | 企业可触达的市场 |
| SOM (可获得市场) | {som} | 企业实际可获取份额 |

**市场空间评估**: {tam} 的总市场空间，企业目标获取 {som} 的市场份额。
""")
    
    # ═════════════════════════════════════════
    # 四、竞争格局与主要玩家
    # ═════════════════════════════════════════
    report.append("\n---\n")
    report.append("## 四、竞争格局与主要玩家\n")
    
    compe_data = search_results.get("竞品", "暂无数据")
    report.append(compe_data)
    
    # ═════════════════════════════════════════
    # 五、投资建议
    # ═════════════════════════════════════════
    report.append("\n---\n")
    report.append("## 五、投资建议\n")
    
    # 综合评分
    pest_avg = avg_score
    porter_score = 5 - (high_count * 0.5)  # 竞争越激烈分数越低
    
    overall = (pest_avg + porter_score) / 2
    
    if overall >= 3.5:
        suggestion = "🟢 **推荐关注** — 行业环境良好，竞争格局可控，建议深入研究龙头标的"
    elif overall >= 2.5:
        suggestion = "🟡 **谨慎观望** — 行业存在一定挑战，需精选标的，关注竞争优势明显的龙头"
    else:
        suggestion = "🔴 **暂不推荐** — 行业环境较差或竞争激烈，投资风险较高"
    
    report.append(f"""
### 综合评估

| 维度 | 评分 | 权重 |
|------|------|------|
| PEST宏观环境 | {pest_avg:.1f}/5 | 40% |
| 竞争格局 | {porter_score:.1f}/5 | 40% |
| 市场空间 | 评估中 | 20% |

**综合得分**: {overall:.1f}/5

{suggestion}
""")
    
    return "\n".join(report)


def _score_dimension(content):
    """根据内容长度和关键词简单评分"""
    if not content or content == "暂无数据":
        return 3
    
    # 关键词判断
    positive_keywords = ["增长", "扩张", "利好", "支持", "鼓励", "突破", "创新", "上升"]
    negative_keywords = ["下滑", "萎缩", "限制", "收紧", "下降", "冲击", "风险"]
    
    positive_count = sum(1 for kw in positive_keywords if kw in content)
    negative_count = sum(1 for kw in negative_keywords if kw in content)
    
    base = 3
    base += min(positive_count * 0.3, 1.5)
    base -= min(negative_count * 0.3, 1.5)
    
    return max(1, min(5, round(base)))


def _assess_force_intensity(content):
    """评估竞争力量强度"""
    if not content or content == "暂无数据":
        return "中"
    
    high_keywords = ["激烈", "高", "强", "众多", "集中度高", "龙头"]
    low_keywords = ["低", "弱", "少", "分散", "门槛高"]
    
    for kw in high_keywords:
        if kw in content:
            return "高"
    
    for kw in low_keywords:
        if kw in content:
            return "低"
    
    return "中"


def save_report(report, output_dir, industry_name):
    """保存报告到文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存报告
    report_path = os.path.join(output_dir, f"行业分析_{industry_name}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 报告已保存: {report_path}")
    return report_path


# ─────────────────────────────────────────────
# CLI入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="行业深度分析 V2 - AI驱动版")
    parser.add_argument("--industry", required=True, help="行业名称")
    parser.add_argument("--year", type=int, default=2026, help="研究年度")
    parser.add_argument("--output", default=None, help="输出目录")
    parser.add_argument("--mode", choices=["query", "report"], default="query",
                       help="query: 输出搜索任务 | report: 从JSON生成报告")
    parser.add_argument("--data", default=None, help="搜索结果JSON文件(report模式)")
    
    args = parser.parse_args()
    
    if args.mode == "query":
        # 输出AI需要搜集的数据结构
        queries = build_search_queries(args.industry, args.year)
        print(json.dumps(queries, ensure_ascii=False, indent=2))
        print("\n" + "="*60)
        print("👆 请AI用web_search搜集以上数据，结果保存为JSON后传入 --data 参数")
    
    elif args.mode == "report":
        if not args.data:
            print("❌ report模式需要 --data 参数指定JSON文件")
            sys.exit(1)
        
        with open(args.data, 'r', encoding='utf-8') as f:
            search_results = json.load(f)
        
        report = generate_report(args.industry, search_results, args.year)
        
        output_dir = args.output or f"output/industry_{args.industry}_{datetime.now().strftime('%Y%m%d')}"
        save_report(report, output_dir, args.industry)
        print("\n" + report)
