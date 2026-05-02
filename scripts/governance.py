# -*- coding: utf-8 -*-
"""
公司治理深度分析模块
数据源: 东方财富 RPT_F10_EQUITY_HOLDER / RPT_F10_MANAGE_MAININFO / RPT_F10_EQUITY_PLEDGE
功能: 股权集中度、大股东质押、管理层信息、独董有效性、审计信息、内控评价
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
from scripts.safe_request import safe_get, safe_extract, safe_float

EM_API = "http://datacenter-web.eastmoney.com/api/data/v1/get"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "http://data.eastmoney.com/",
    "Accept": "application/json",
}


def _secucode(stock_code):
    if stock_code.endswith((".SH", ".SZ", ".BJ")):
        return stock_code
    if stock_code[:2] in ["00", "30"]:
        return f"{stock_code}.SZ"
    if stock_code[:2] in ["60", "68"]:
        return f"{stock_code}.SH"
    if stock_code[0] in ["8", "4"]:
        return f"{stock_code}.BJ"
    return f"{stock_code}.SZ"


def fetch_governance(stock_code, market="a", data_dir=None):
    """主函数：治理分析"""
    result = {
        "stock_code": stock_code,
        "top_shareholders": [],
        "ownership": {},
        "pledge": {},
        "management": {},
        "independent_directors": {},
        "auditor": {},
        "internal_control": {},
        "score": 0,
        "risks": [],
        "warnings": [],
    }

    secucode = _secucode(stock_code)
    result["top_shareholders"] = _fetch_top_shareholders(secucode)
    result["ownership"] = _analyze_ownership(result["top_shareholders"])
    result["pledge"] = _fetch_pledge_info(secucode)
    result["management"] = _fetch_management(secucode)
    result["independent_directors"] = _analyze_independent_directors(result["management"])
    result["auditor"] = _fetch_auditor(secucode)
    result["internal_control"] = _fetch_internal_control(secucode)
    result["score"] = _governance_score(result)
    result["risks"] = _summarize_governance_risks(result)

    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "governance.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    return result


def _fetch_top_shareholders(secucode):
    """使用AKShare获取前十大股东"""
    try:
        import akshare as ak
        # 转换为AKShare格式：sh/sz/bj前缀
        if secucode.endswith('.SH'):
            prefix = 'sh'
        elif secucode.endswith('.SZ'):
            prefix = 'sz'
        elif secucode.endswith('.BJ'):
            prefix = 'bj'
        else:
            prefix = 'sh'
        ak_code = prefix + secucode.split('.')[0]
        
        df = ak.stock_gdfx_top_10_em(symbol=ak_code)
        if df.empty:
            return []
        
        result = []
        for _, row in df.head(10).iterrows():
            ratio = safe_float(row.get('占总股本持股比例'))
            if ratio is not None:
                result.append({
                    "name": str(row.get('股东名称', '未知')),
                    "ratio_pct": round(ratio, 2),
                    "type": str(row.get('股份类型', '未知')),
                    "change": row.get('增减'),
                    "date": '',
                })
        return result
    except Exception as e:
        return []


def _analyze_ownership(top_sh):
    if not top_sh:
        return {"type": "未知", "cr1": None, "cr5": None, "cr10": None, "signal": "数据不足"}
    ratios = [s["ratio_pct"] for s in top_sh if s.get("ratio_pct")]
    cr1 = ratios[0] if ratios else None
    cr5 = sum(ratios[:5]) if len(ratios) >= 5 else sum(ratios)
    cr10 = sum(ratios[:10]) if len(ratios) >= 10 else sum(ratios)

    if cr1 and cr1 > 60:
        otype, signal = "高度集中", "一股独大，决策风险集中"
    elif cr1 and cr1 > 30:
        otype, signal = "适度集中", "股权相对集中，大股东控制力较强"
    else:
        otype, signal = "相对分散", "股权相对分散，治理结构更均衡"

    return {"type": otype, "cr1": cr1, "cr5": round(cr5, 2), "cr10": round(cr10, 2), "signal": signal}


def _fetch_pledge_info(secucode):
    """质押信息 - AKShare补全"""
    try:
        import akshare as ak
        stock_code = secucode.split('.')[0]  # 002180
        df = ak.stock_gpzy_individual_pledge_ratio_detail_em(symbol=stock_code)
        if df is None or df.empty:
            return {"records": [], "latest_ratio": None, "signal": "正常（无质押数据）"}
        
        records = []
        for _, row in df.iterrows():
            records.append({
                "pledgor": str(row.get('股东名称', '')),
                "pledge_shares": str(row.get('质押股份数量', '')),
                "pledge_ratio_held": safe_float(row.get('占所持股份比例')),
                "pledge_ratio_total": safe_float(row.get('占总股本比例')),
                "institution": str(row.get('质押机构', '')),
            })
        
        # 计算第一大股东质押率（取质押比例最高者）
        max_pledge_ratio = 0
        for r in records:
            ratio = r.get('pledge_ratio_held') or 0
            if ratio and ratio > max_pledge_ratio:
                max_pledge_ratio = ratio
        
        latest_ratio = max_pledge_ratio / 100 if max_pledge_ratio > 1 else max_pledge_ratio
        
        signal = "正常"
        if latest_ratio and latest_ratio > 0.8:
            signal = "⚠️ 质押率超80%警戒线"
        elif latest_ratio and latest_ratio > 0.5:
            signal = "⚠️ 质押率偏高"
        elif latest_ratio and latest_ratio > 0:
            signal = f"质押率{latest_ratio:.0%}"
        
        return {
            "records": records[:10],
            "latest_ratio": latest_ratio,
            "signal": signal,
            "pledge_count": len(records),
        }
    except ImportError:
        return {"records": [], "latest_ratio": None, "signal": "AKShare未安装"}
    except Exception as e:
        return {"records": [], "latest_ratio": None, "signal": f"数据获取失败: {e}"}


def _fetch_management(secucode):
    """管理层信息 - AKShare补全"""
    try:
        import akshare as ak
        stock_code = secucode.split('.')[0]
        # 东方财富高管列表
        df = ak.stock_gdfx_holding_detail_em(symbol=stock_code)
        if df is None or df.empty:
            return _fetch_management_fallback()
        return _fetch_management_fallback()  # 后续完善
    except:
        return _fetch_management_fallback()

def _fetch_management_fallback():
    return {
        "executives": [],
        "chairman": None,
        "general_manager": None,
        "cfo": None,
        "board_secretary": None,
        "total_count": 0
    }


def _analyze_independent_directors(mgmt):
    execs = mgmt.get("executives", [])
    id_list = [e for e in execs if "独立" in e.get("position", "")]
    total = len(execs)
    ratio = round(len(id_list) / total * 100, 1) if total > 0 else 0
    has_acct = any("会计" in e.get("education", "") or "财务" in e.get("position", "") for e in id_list)
    has_law = any("法律" in e.get("education", "") or "律师" in e.get("position", "") for e in id_list)

    if ratio >= 33 and (has_acct or has_law):
        score = "良好"
    elif ratio >= 33:
        score = "一般"
    else:
        score = "⚠️独董占比不足"

    return {"count": len(id_list), "ratio_pct": ratio,
            "has_accounting_expert": has_acct, "has_law_expert": has_law,
            "independence_score": score, "list": id_list}


def _fetch_auditor(secucode):
    """审计信息 - 尝试从东方财富F10获取"""
    try:
        params = {
            'reportName': 'RPT_F10_AUDIT',
            'columns': 'ALL',
            'filter': f'(SECUCODE="{secucode}")',
            'pageNumber': 1, 'pageSize': 3,
            'sortTypes': -1, 'sortColumns': 'REPORTDATE',
            'source': 'WEB', 'client': 'WEB',
        }
        raw = safe_get(EM_API, params=params, headers=HEADERS, timeout=10)
        records = safe_extract(raw, ['result', 'data'], default=[])
        if records:
            latest = records[0]
            return {
                "auditor": latest.get('AUDITAGENCY'),
                "fee": latest.get('AUDITFEE'),
                "opinion": latest.get('AUDITOPINION'),
                "years": len(records),
                "latest_year": str(latest.get('REPORTDATE', ''))[:4],
            }
    except:
        pass
    return {"auditor": None, "fee": None, "opinion": None, "years": 0, "latest_year": None}


def _fetch_internal_control(secucode):
    """内控信息 - 东方财富API已失效，优雅降级"""
    return {"opinion": "暂无数据", "self_eval": None, "audit_opinion": None, "year": None}


def _governance_score(result):
    score = 50
    ow = result.get("ownership", {})
    if ow.get("cr1"):
        if ow["cr1"] > 60:
            score -= 15
        elif ow["cr1"] < 30:
            score += 10
    idd = result.get("independent_directors", {})
    if idd.get("ratio_pct", 0) >= 33:
        score += 10
    if idd.get("has_accounting_expert"):
        score += 5
    if idd.get("has_law_expert"):
        score += 5
    aud = result.get("auditor", {})
    if aud.get("auditor"):
        score += 10
    if "非标" in str(aud.get("opinion", "")):
        score -= 20
    pledge = result.get("pledge", {})
    if pledge.get("latest_ratio"):
        if pledge["latest_ratio"] > 80:
            score -= 15
        elif pledge["latest_ratio"] > 50:
            score -= 5
    ic = result.get("internal_control", {})
    if "缺陷" in str(ic.get("opinion", "")):
        score -= 10
    return max(0, min(100, score))


def _summarize_governance_risks(result):
    risks = []
    ow = result.get("ownership", {})
    if ow.get("cr1") and ow["cr1"] > 60:
        risks.append({"level": "medium", "dim": "治理", "signal": f"一股独大(CR1={ow['cr1']:.1f}%)"})
    pledge = result.get("pledge", {})
    if pledge.get("latest_ratio") and pledge["latest_ratio"] > 80:
        risks.append({"level": "high", "dim": "治理", "signal": f"大股东质押比例偏高({pledge['latest_ratio']:.1f}%)"})
    elif pledge.get("latest_ratio") and pledge["latest_ratio"] > 50:
        risks.append({"level": "medium", "dim": "治理", "signal": f"质押比例{pledge['latest_ratio']:.1f}%"})
    aud = result.get("auditor", {})
    if aud.get("opinion") and "非标" in str(aud["opinion"]):
        risks.append({"level": "high", "dim": "治理", "signal": f"审计意见: {aud['opinion']}"})
    ic = result.get("internal_control", {})
    if "缺陷" in str(ic.get("opinion", "")):
        risks.append({"level": "medium", "dim": "治理", "signal": "内控存在缺陷"})
    return risks


def format_markdown(data):
    if not data:
        return "## 公司治理分析\n\n_暂无数据_"

    ow = data.get("ownership", {})
    mgmt = data.get("management", {})
    idd = data.get("independent_directors", {})
    aud = data.get("auditor", {})
    ic = data.get("internal_control", {})
    pledge = data.get("pledge", {})
    top_sh = data.get("top_shareholders", [])
    score = data.get("score", 0)
    risks = data.get("risks", [])

    lines = ["## 公司治理深度分析\n"]
    sc = "🟢" if score >= 70 else ("🟡" if score >= 50 else "🔴")
    lines.append(f"### 治理评分: {sc} **{score}/100**\n")

    lines.append("### 股权结构与集中度\n")
    lines.append(f"- 股权类型: {ow.get('type', '未知')} | CR1: **{ow.get('cr1', 'N/A')}%** | CR5: **{ow.get('cr5', 'N/A')}%** | CR10: **{ow.get('cr10', 'N/A')}%**")
    lines.append(f"- 信号: {ow.get('signal', '数据不足')}")
    if top_sh:
        lines.append("\n**前十大股东**:")
        lines.append("| 股东名称 | 持股比例 | 股东类型 |")
        lines.append("|----------|---------|---------|")
        for sh in top_sh[:5]:
            lines.append(f"| {sh.get('name', '?')[:20]} | {sh.get('ratio_pct', '?')}% | {sh.get('type', '?')} |")
    lines.append("")

    lines.append("### 股份质押\n")
    pl_ratio = pledge.get("latest_ratio")
    lines.append(f"- 最新质押比例: **{pl_ratio:.1f}%** → {pledge.get('signal', '暂无数据')}" if pl_ratio else "- 暂无质押数据")
    for r in pledge.get("records", [])[:3]:
        lines.append(f"  - {r.get('date', '')}: {r.get('pledgor', '?')} → {r.get('pledgee', '?')}（{r.get('ratio', '?')}%）")
    lines.append("")

    lines.append("### 管理层\n")
    for role, label in [("chairman", "董事长"), ("general_manager", "总经理"), ("cfo", "财务总监"), ("board_secretary", "董秘")]:
        p = mgmt.get(role)
        if p:
            lines.append(f"- {label}: {p.get('name', '?')}（{p.get('education', '?')}）")
    lines.append("")

    lines.append("### 独立董事\n")
    lines.append(f"- 独董人数: {idd.get('count', 0)}，占比: {idd.get('ratio_pct', 0)}%")
    lines.append(f"- 有效性评估: {idd.get('independence_score', '数据不足')}")
    if idd.get("has_accounting_expert"):
        lines.append("- ✓ 有会计背景独董")
    if idd.get("has_law_expert"):
        lines.append("- ✓ 有法律背景独董")
    lines.append("")

    lines.append("### 审计信息\n")
    lines.append(f"- 审计机构: {aud.get('auditor', '未知')}")
    if aud.get("fee"):
        lines.append(f"- 审计费用: {aud['fee']:.0f}万元/年")
    if aud.get("opinion"):
        lines.append(f"- 审计意见: **{aud['opinion']}**")
    if aud.get("years"):
        lines.append(f"- 合作年限: {aud['years']}年")
    lines.append("")

    lines.append("### 内控评价\n")
    lines.append(f"- 内控意见: {ic.get('opinion', '暂无数据')}")
    if ic.get("self_eval"):
        lines.append(f"- 自评结论: {ic['self_eval']}")
    lines.append("")

    if risks:
        lines.append("### 治理风险信号\n")
        for r in risks:
            icon = "🔴" if r["level"] == "high" else "🟡"
            lines.append(f"- {icon} [{r['dim']}] {r['signal']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    stock = sys.argv[1] if len(sys.argv) > 1 else "600519"
    data = fetch_governance(stock, data_dir="output/test")
    print(format_markdown(data))
