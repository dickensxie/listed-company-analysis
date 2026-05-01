# -*- coding: utf-8 -*-
"""
投行综合研究工作台
IB Research Workbench — 联动 listed-company-analysis + 行业分析 + 研报快讯

用法:
  python research_workflow.py --stock 002180                    # 公司+行业全分析
  python research_workflow.py --stock 002180 --skip-industry    # 仅公司分析
  python research_workflow.py --industry "中国半导体行业"        # 仅行业深度分析
  python research_workflow.py --stock 002180 --dims company,industry,macro,risk
  python research_workflow.py --report-link "https://..."        # 分析研报并输出180k快讯
  python research_workflow.py --company "极海微" --type unlisted # 未上市公司全调

工作流层次:
  Layer 1 — 公司层 (listed-company-analysis)
  Layer 2 — 行业层 (PEST+波特五力+TAM)
  Layer 3 — 宏观层 (宏观环境+板块周期)
  Layer 4 — 研报层 (卖方研报→投研快讯)
  Layer 5 — 风控层 (多角色审查)
"""
import sys, os, argparse, json, re, time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')


# ─────────────────────────────────────────────
# Layer 1: 公司层分析
# ─────────────────────────────────────────────

def run_company_analysis(stock_code, market="auto", dims="all", output_dir=None,
                          full_analysis=False, skip_pdf=False, skip_peer=False):
    """
    调用 listed-company-analysis 的核心分析
    """
    print(f"\n{'='*60}")
    print(f"【Layer 1】上市公司分析: {stock_code} ({market})")
    print(f"{'='*60}")

    # 动态导入，避免循环依赖
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from scripts.analyze import run_analysis

        args = argparse.Namespace(
            stock=stock_code,
            name=None,
            company=None,
            market=market,
            dims=dims,
            full=full_analysis,
            output=output_dir,
            no_pdf=skip_pdf,
            no_peer=skip_peer,
        )

        # 捕获输出文件路径
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'output', f'{stock_code}_{datetime.now().strftime("%Y%m%d_%H%M")}'
            )

        os.makedirs(output_dir, exist_ok=True)
        args.output = output_dir

        result = run_analysis(args)

        # 找最新报告文件
        report_file = None
        if os.path.exists(output_dir):
            files = sorted(
                [f for f in os.listdir(output_dir) if f.endswith('.md')],
                key=os.path.getmtime,
                reverse=True
            )
            if files:
                report_file = os.path.join(output_dir, files[0])

        return {
            "layer": "company",
            "stock_code": stock_code,
            "market": market,
            "output_dir": output_dir,
            "report_file": report_file,
            "result": result,
        }

    except ImportError as e:
        return {
            "layer": "company",
            "stock_code": stock_code,
            "error": f"导入分析模块失败: {e}",
        }
    except Exception as e:
        return {
            "layer": "company",
            "stock_code": stock_code,
            "error": f"公司分析失败: {e}",
        }


# ─────────────────────────────────────────────
# Layer 2: 行业层分析
# ─────────────────────────────────────────────

def run_industry_analysis(industry_name, year=2026, output_dir=None, search_results=None):
    """
    调用行业分析模块 V2 - AI驱动版
    
    参数:
        industry_name: 行业名称
        year: 研究年度
        output_dir: 输出目录
        search_results: AI通过online-search搜集的数据(dict)
                       如果为None，则输出搜索任务让AI执行
    """
    print(f"\n{'='*60}")
    print(f"【Layer 2】行业分析: {industry_name}")
    print(f"{'='*60}")

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        if search_results:
            # AI已提供搜索结果，直接生成报告
            from scripts.industry_analysis_v2 import generate_report, save_report
            
            report = generate_report(industry_name, search_results, year)
            
            if output_dir is None:
                output_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'output', f'industry_{industry_name}_{datetime.now().strftime("%Y%m%d")}'
                )
            
            report_path = save_report(report, output_dir, industry_name)
            
            return {
                "layer": "industry",
                "industry": industry_name,
                "output_dir": output_dir,
                "report_file": report_path,
                "status": "success",
            }
        else:
            # 未提供搜索结果，输出搜索任务
            from scripts.industry_analysis_v2 import build_search_queries
            
            queries = build_search_queries(industry_name, year)
            
            print("\n⚠️ 行业分析需要AI搜集数据，请执行以下步骤:")
            print("1. 用 online-search Skill 搜集以上queries中的数据")
            print("2. 将搜索结果整理为JSON格式")
            print("3. 重新调用时传入 search_results 参数")
            
            return {
                "layer": "industry",
                "industry": industry_name,
                "status": "pending",
                "queries": queries,
                "message": "需要AI搜集数据后重新调用",
            }
            
    except Exception as e:
        return {
            "layer": "industry",
            "industry": industry_name,
            "error": f"行业分析失败: {e}",
        }


# ─────────────────────────────────────────────
# Layer 3: 宏观/板块背景分析
# ─────────────────────────────────────────────

def run_macro_context(stock_code, market="a", output_dir=None):
    """
    搜集宏观环境 + 板块周期背景
    为公司分析提供宏观锚点
    """
    print(f"\n{'='*60}")
    print(f"【Layer 3】宏观/板块背景: {stock_code}")
    print(f"{'='*60}")

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from scripts.industry import fetch_industry

        industry_info = fetch_industry(stock_code, market, output_dir)

        # 尝试获取板块实时行情（大盘背景）
        try:
            from scripts.bse_price import fetch_price
            if market in ("a", "auto") and len(stock_code) <= 6:
                price_data = fetch_price(stock_code, market)
                has_price = True
            else:
                has_price = False
        except Exception:
            has_price = False
            price_data = None

        # 尝试获取市场指数（判断板块强弱）
        index_map = {
            "a": {"index": "上证指数", "code": "sh000001"},
            "hk": {"index": "恒生指数", "code": "hkHSI"},
        }

        macro_data = {
            "stock_code": stock_code,
            "market": market,
            "industry_info": industry_info,
            "index_data": index_map.get(market, {}),
            "has_price": has_price,
            "price_data": price_data,
        }

        return {
            "layer": "macro",
            "stock_code": stock_code,
            "data": macro_data,
            "output_dir": output_dir,
        }
    except Exception as e:
        return {
            "layer": "macro",
            "stock_code": stock_code,
            "error": f"宏观背景获取失败: {e}",
        }


# ─────────────────────────────────────────────
# Layer 4: 研报快讯（180k风格）
# ─────────────────────────────────────────────

def run_research_brief(report_content=None, report_url=None, stock_code=None,
                        output_dir=None):
    """
    将研报转化为180k风格投研快讯
    调用 research-summary skill 的方法论
    """
    print(f"\n{'='*60}")
    print(f"【Layer 4】研报快讯生成")
    print(f"{'='*60}")

    brief_content = ""

    if report_url:
        print(f"  → 抓取研报: {report_url}")
        try:
            from web_fetch import web_fetch
            content = web_fetch(report_url)
            report_text = content[:5000] if content else ""
        except Exception:
            report_text = f"[从URL抓取失败，请参考: {report_url}]"
    elif report_content:
        report_text = report_content
    else:
        return {"layer": "brief", "error": "无研报内容"}

    # 简单格式化为快讯（实际由LLM在这里做深度格式化）
    brief_content = f"""
# 📋 投研快讯
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**关联标的**: {stock_code or 'N/A'}
**来源**: {report_url or '直接输入'}

---

## 报告概要

{report_text[:3000]}

---

> 💡 **使用说明**: 以上为研报原始摘要。请结合 listed-company-analysis 的完整公司分析，
> 输出真正的"180k风格"投研快讯——先给判断，再给证据，重点提炼预期差。
"""

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "research_brief.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(brief_content)
        print(f"  ✅ 快讯草稿已保存: {out_path}")

    return {
        "layer": "brief",
        "brief_content": brief_content,
        "report_text": report_text[:2000],
        "output_dir": output_dir,
    }


# ─────────────────────────────────────────────
# Layer 5: 风控审查（sub-agent模式）
# ─────────────────────────────────────────────

def run_risk_review(company_report_text, industry_report_text="", stock_code=""):
    """
    启动独立风控审查
    参考 company-research-cn 的多角色工作流
    """
    print(f"\n{'='*60}")
    print(f"【Layer 5】风控官审查: {stock_code}")
    print(f"{'='*60}")
    print("  ⚠️ 风控审查需启动独立 sub-agent，以下为结构化审查框架...")

    # 构建风控审查 prompt（供主session或sub-agent使用）
    risk_review_prompt = f"""
# 风控审查报告 — {stock_code}

## 审查任务
对以下研究报告进行独立风控审查，重点识别：
1. 遗漏的重大风险
2. 乐观假设或偏见
3. 数据可靠性问题
4. 监管/合规隐患

---

## 公司研究报告摘要
{company_report_text[:5000]}

---

## 行业研究报告摘要（如有）
{industry_report_text[:3000] if industry_report_text else "[无行业报告]"}
"""

    # 预定义风控审查维度（框架，不依赖sub-agent即可用）
    risk_dimensions = {
        "财务风险": {
            "检查点": [
                "商誉减值风险是否充分揭示？",
                "现金流与利润是否背离？",
                "应收账款账龄和回款风险？",
                "关联交易定价合理性？",
                "研发支出资本化比例是否激进？",
            ],
            "关注等级": "🔴高"
        },
        "经营风险": {
            "检查点": [
                "大客户集中度风险？",
                "供应商依赖风险？",
                "产能利用率是否有周期性波动？",
                "核心技术人员稳定性？",
                "产品结构单一风险？",
            ],
            "关注等级": "🟡中"
        },
        "治理风险": {
            "检查点": [
                "实控人股权质押比例？",
                "同业竞争是否解决？",
                "关联交易频繁程度？",
                "独董履职有效性？",
                "内部控制缺陷历史？",
            ],
            "关注等级": "🟡中"
        },
        "监管风险": {
            "检查点": [
                "行政处罚历史是否充分披露？",
                "重大诉讼/仲裁进展？",
                "行业监管政策重大变化？",
                "IPO/分拆合规障碍？",
            ],
            "关注等级": "🔴高"
        },
        "市场风险": {
            "检查点": [
                "竞争格局变化风险？",
                "技术替代风险？",
                "周期性行业下行风险？",
                "汇率/大宗商品敞口？",
            ],
            "关注等级": "🟡中"
        },
    }

    risk_output = ["# 风控审查报告\n"]
    risk_output.append(f"**审查标的**: {stock_code or 'N/A'}")
    risk_output.append(f"**审查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    risk_output.append(f"**审查方法**: 结构化风险清单 + 信号驱动\n")
    risk_output.append("---\n")

    for risk_type, info in risk_dimensions.items():
        risk_output.append(f"## {risk_type} [{info['关注等级']}]\n")
        risk_output.append("| # | 检查点 | 状态 | 备注 |")
        risk_output.append("|---|--------|------|------|")
        for i, check in enumerate(info["检查点"], 1):
            # 简单判断：有相关信号=⚠️需关注，无=✅暂无明显问题
            relevant = any(
                kw in (company_report_text + industry_report_text)
                for kw in [check[:4], check.split('？')[0]]
            )
            status = "⚠️ 需关注" if relevant else "✅ 暂无明显问题"
            risk_output.append(f"| {i} | {check} | {status} | _ |")
        risk_output.append("")

    return {
        "layer": "risk_review",
        "risk_prompt": risk_review_prompt,
        "risk_framework": risk_dimensions,
        "risk_report": "\n".join(risk_output),
        "stock_code": stock_code,
    }


# ─────────────────────────────────────────────
# 综合工作台主入口
# ─────────────────────────────────────────────

def run_research_workflow(stock_code=None, company_name=None,
                          industry_name=None,
                          market="auto",
                          dims="all",
                          full_analysis=False,
                          report_url=None,
                          report_content=None,
                          run_industry=True,
                          run_macro=True,
                          run_risk_review=False,
                          output_dir=None):
    """
    投行综合研究工作台主函数

    参数:
      stock_code: 股票代码（A股/港股/美股）
      company_name: 公司名称（跨市场识别）
      industry_name: 行业名称（如：半导体、新能源汽车）
      market: 市场（auto/a/hk/us）
      dims: 公司分析维度
      full_analysis: 完整分析（含年报PDF）
      report_url: 研报URL → 生成研报快讯
      report_content: 研报内容 → 生成研报快讯
      run_industry: 是否执行行业分析
      run_macro: 是否搜集宏观/板块背景
      run_risk_review: 是否执行风控审查
      output_dir: 输出目录
    """
    start_time = datetime.now()
    results = {}

    # 确定输出目录
    if output_dir is None:
        target = stock_code or company_name or industry_name or "research"
        safe_target = re.sub(r'[^\w\u4e00-\u9fa5]', '_', target)
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'output',
            f'workbench_{safe_target}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        )
    os.makedirs(output_dir, exist_ok=True)

    # ── Layer 1: 公司层 ──
    if stock_code or company_name:
        results["layer1_company"] = run_company_analysis(
            stock_code=stock_code,
            market=market,
            dims=dims,
            output_dir=output_dir,
            full_analysis=full_analysis,
        )

        # 读取公司报告文本供后续使用
        company_report_text = ""
        l1 = results.get("layer1_company", {})
        rf = l1.get("report_file")
        if rf and os.path.exists(rf):
            with open(rf, encoding="utf-8") as f:
                company_report_text = f.read()

        # ── Layer 2: 行业层 ──
        if run_industry and industry_name:
            results["layer2_industry"] = run_industry_analysis(
                industry_name, output_dir=output_dir
            )
        elif run_industry and stock_code:
            # 从公司报告中推断行业
            industry_from_report = _infer_industry(company_report_text)
            if industry_from_report:
                results["layer2_industry"] = run_industry_analysis(
                    industry_from_report, output_dir=output_dir
                )

        # ── Layer 3: 宏观/板块层 ──
        if run_macro and stock_code:
            results["layer3_macro"] = run_macro_context(
                stock_code, market, output_dir
            )

        # ── Layer 4: 研报快讯 ──
        if report_url or report_content:
            results["layer4_brief"] = run_research_brief(
                report_content=report_content,
                report_url=report_url,
                stock_code=stock_code,
                output_dir=output_dir,
            )

        # ── Layer 5: 风控审查 ──
        if run_risk_review and company_report_text:
            industry_report_text = ""
            l2 = results.get("layer2_industry", {})
            r2 = l2.get("result", {})
            if isinstance(r2, dict):
                industry_report_text = r2.get("report", "")

            results["layer5_risk"] = run_risk_review(
                company_report_text, industry_report_text, stock_code
            )

    # ── 仅行业分析 ──
    elif industry_name and not stock_code:
        results["layer2_industry"] = run_industry_analysis(
            industry_name, output_dir=output_dir
        )

    # ── 生成综合封面 ──
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    summary = _generate_workbench_summary(results, output_dir, duration)

    # 打印封面
    print(f"\n{'='*60}")
    print("🏦 投行综合研究工作台 — 完成")
    print(f"{'='*60}")
    print(summary["toc"])
    print(summary["outputs"])

    # 保存封面
    summary_path = os.path.join(output_dir, "WORKFLOW_SUMMARY.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary["full_report"])
    print(f"\n📄 综合报告封面: {summary_path}")

    results["_summary"] = summary
    results["_output_dir"] = output_dir
    results["_duration_sec"] = duration

    return results


def _infer_industry(company_report_text):
    """从公司报告中推断行业"""
    industry_keywords = {
        "中国半导体行业": ["半导体", "芯片", "集成电路", "晶圆", "封测", "IC设计"],
        "中国新能源汽车行业": ["新能源汽车", "电动车", "动力电池", "锂电", "汽车电子"],
        "中国生物医药行业": ["生物医药", "创新药", "医疗器械", "CXO", "疫苗", "中药"],
        "中国云计算行业": ["云计算", "SaaS", "IaaS", "数据中心", "公有云"],
        "中国消费电子行业": ["消费电子", "智能手机", "面板", "OLED", "TWS"],
    }

    # 找匹配度最高的
    best_match = None
    best_score = 0
    for industry, keywords in industry_keywords.items():
        score = sum(1 for kw in keywords if kw in company_report_text)
        if score > best_score:
            best_score = score
            best_match = industry

    return best_match if best_score >= 1 else None


def _generate_workbench_summary(results, output_dir, duration):
    """生成工作台综合封面"""
    lines = []
    lines.append("# 🏦 投行综合研究工作台 — 研究报告\n")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**运行时长**: {duration:.1f}秒")
    lines.append(f"**输出目录**: `{output_dir}`")
    lines.append("\n---\n")

    # 目录
    lines.append("## 报告目录\n")

    toc = []
    if "layer1_company" in results:
        l1 = results["layer1_company"]
        sc = l1.get("stock_code", "")
        toc.append(f"- **【Layer 1】公司层分析** → `layer1_company/`")
        toc.append(f"  - 标的: {sc}")
        rf = l1.get("report_file", "")
        if rf:
            fname = os.path.basename(rf)
            toc.append(f"  - 公司深度报告: `{fname}`")

    if "layer2_industry" in results:
        l2 = results["layer2_industry"]
        ind = l2.get("industry", "")
        toc.append(f"- **【Layer 2】行业层分析** → `layer2_industry/`")
        toc.append(f"  - 行业: {ind}")

    if "layer3_macro" in results:
        toc.append(f"- **【Layer 3】宏观/板块背景** → `layer3_macro/`")

    if "layer4_brief" in results:
        toc.append(f"- **【Layer 4】研报快讯** → `layer4_brief/`")

    if "layer5_risk" in results:
        toc.append(f"- **【Layer 5】风控审查** → `layer5_risk/`")

    lines.extend(toc)
    lines.append("\n---\n")

    # 核心发现摘要
    lines.append("## 核心发现摘要\n")

    if "layer1_company" in results:
        l1 = results["layer1_company"]
        rf = l1.get("report_file", "")
        if rf and os.path.exists(rf):
            with open(rf, encoding="utf-8") as f:
                content = f.read()
            # 提取执行摘要（如果有）
            summary_match = re.search(r'(?:## 执行摘要|## 一、.+?摘要)(.*?)(?=##|\Z)',
                                       content, re.DOTALL)
            if summary_match:
                lines.append("### 📊 公司层\n")
                lines.append(summary_match.group(0)[:1500])
            else:
                lines.append(f"_公司分析详见报告全文（{os.path.basename(rf)}）_\n")

    if "layer2_industry" in results:
        l2 = results["layer2_industry"]
        r2 = l2.get("result", {})
        if isinstance(r2, dict):
            ind = l2.get("industry", "")
            lines.append(f"\n### 🏭 行业层 — {ind}\n")
            # 提取PEST和波特五力结论
            report = r2.get("report", "")
            pest_match = re.search(r'## 一、PEST.*?(?=##|\Z)', report, re.DOTALL)
            porter_match = re.search(r'## 二、波特五力.*?(?=##|\Z)', report, re.DOTALL)
            if pest_match:
                lines.append(pest_match.group(0)[:800])
            if porter_match:
                lines.append(porter_match.group(0)[:600])

    if "layer5_risk" in results:
        l5 = results["layer5_risk"]
        risk_report = l5.get("risk_report", "")
        lines.append("\n### ⚠️ 风控要点\n")
        # 提取高风险项
        for line in risk_report.split('\n'):
            if '🔴高' in line or '⚠️ 需关注' in line:
                lines.append(line + "\n")

    lines.append("\n---\n")
    lines.append("## 工具链\n")
    lines.append("- **公司分析**: listed-company-analysis (多市场, 23+维度)")
    lines.append("- **行业分析**: PEST + 波特五力 + TAM/SAM/SOM + 价值链")
    lines.append("- **宏观背景**: 板块行情 + 行业景气度")
    lines.append("- **研报快讯**: 180k风格（research-summary方法论）")
    lines.append("- **风控审查**: 五维度结构化风险清单")
    lines.append("\n> ⚠️ 本工作台报告均为内部研究参考，不构成投资建议。\n")

    full_report = "\n".join(lines)
    toc_only = "\n".join(toc)
    outputs = f"输出目录: {output_dir}"

    return {
        "full_report": full_report,
        "toc": toc_only,
        "outputs": outputs,
    }


# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🏦 投行综合研究工作台 — 公司+行业+宏观+研报+风控",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python research_workflow.py --stock 002180 --full-analysis
  python research_workflow.py --stock 002180 --dims risk,valuation,peer
  python research_workflow.py --industry "中国半导体行业"
  python research_workflow.py --stock 002180 --run-risk-review
  python research_workflow.py --report-url "https://..."
  python research_workflow.py --company "极海微" --type unlisted
        """
    )

    parser.add_argument('--stock', help='股票代码（A/H/美股）')
    parser.add_argument('--name', help='公司名称（跨市场自动识别）')
    parser.add_argument('--company', help='公司名称（未上市公司）')
    parser.add_argument('--industry', help='行业名称（独立行业分析）')
    parser.add_argument('--market', default='auto',
                        choices=['auto', 'a', 'hk', 'us'],
                        help='市场（默认auto自动识别）')
    parser.add_argument('--dims', default='all',
                        help='分析维度: all/company/risk/valuation/peer/industry/macro/brief')
    parser.add_argument('--full-analysis', action='store_true',
                        help='完整分析（含年报PDF提取）')
    parser.add_argument('--skip-industry', action='store_true',
                        help='跳过行业分析')
    parser.add_argument('--skip-macro', action='store_true',
                        help='跳过宏观背景')
    parser.add_argument('--run-risk-review', action='store_true',
                        help='执行五维度风控审查')
    parser.add_argument('--report-url', help='研报URL → 生成180k快讯')
    parser.add_argument('--report-file', help='研报文本文件路径')
    parser.add_argument('--output', help='输出目录')
    parser.add_argument('--type', default='listed',
                        choices=['listed', 'unlisted'],
                        help='公司类型（默认上市公司）')

    args = parser.parse_args()

    # 处理研报内容
    report_content = None
    if args.report_file and os.path.exists(args.report_file):
        with open(args.report_file, encoding="utf-8") as f:
            report_content = f.read()

    # 解析dims
    dim_map = {
        'all': 'all',
        'company': 'announcements,financial,executives,capital,subsidiary,related,regulatory,structure',
        'risk': 'risk,regulatory,executives',
        'valuation': 'financial,valuation,peer,multi_year',
        'peer': 'peer,industry',
        'industry': 'industry',
        'macro': 'macro',
        'brief': 'brief',
    }
    dims = dim_map.get(args.dims, 'all')

    # 判断是公司分析还是行业分析
    run_industry_only = bool(args.industry) and not args.stock and not args.name and not args.company

    if run_industry_only:
        # 纯行业分析
        print(f"\n🏭 行业深度研究: {args.industry}")
        result = run_industry_analysis(args.industry, output_dir=args.output)
        if result.get("result"):
            print(result["result"]["report"])
    else:
        # 公司+可选行业
        result = run_research_workflow(
            stock_code=args.stock,
            company_name=args.name,
            industry_name=args.industry,
            market=args.market,
            dims=dims,
            full_analysis=args.full_analysis,
            report_url=args.report_url,
            report_content=report_content,
            run_industry=not args.skip_industry,
            run_macro=not args.skip_macro,
            run_risk_review=args.run_risk_review,
            output_dir=args.output,
        )

        # 打印最终综合报告
        summary = result.get("_summary", {})
        print("\n" + summary.get("full_report", ""))
