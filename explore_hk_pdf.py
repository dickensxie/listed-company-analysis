"""
探索港股HKEX披露易的PDF下载方法
"""
import requests
import re
import json
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

print("=" * 60)
print("港股HKEX披露易PDF探索")
print("=" * 60)

# 方案1：HKEX披露易搜索页面
print("\n[方案1] HKEX披露易搜索页面")
stock_code = "00700"
search_url = f"https://www1.hkexnews.hk/search/titlesearch?lang=zh-HK&issuerId={stock_code}&titleId=&titleType=A"
print(f"URL: {search_url}")

try:
    r = requests.get(search_url, headers=headers, timeout=30, allow_redirects=True)
    print(f"状态码: {r.status_code}")
    print(f"最终URL: {r.url}")
    print(f"响应长度: {len(r.text)} 字符")
    
    # 检查是否是SPA
    if '<script' in r.text and 'window.__INITIAL_STATE__' in r.text:
        print("检测到SPA架构（包含__INITIAL_STATE__）")
        # 尝试提取初始数据
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', r.text, re.DOTALL)
        if match:
            print("找到__INITIAL_STATE__数据（可能包含公告列表）")
    
    # 查找PDF链接
    pdf_pattern = r'href="([^"]+\.pdf)"'
    pdfs = re.findall(pdf_pattern, r.text)
    if pdfs:
        print(f"\n找到 {len(pdfs)} 个PDF链接:")
        for pdf in pdfs[:5]:
            print(f"  - {pdf}")
    else:
        print("未找到PDF链接（可能需要JS渲染）")
        
except Exception as e:
    print(f"错误: {e}")

# 方案2：HKEX newsweb主站
print("\n" + "=" * 60)
print("[方案2] HKEX Newsweb主页")
news_url = f"https://www1.hkexnews.hk/index.htm"
print(f"URL: {news_url}")

try:
    r = requests.get(news_url, headers=headers, timeout=30)
    print(f"状态码: {r.status_code}")
    
    # 查找API端点或JS变量
    if 'api' in r.text.lower():
        api_matches = re.findall(r'["\']([^"\']*api[^"\']*)["\']', r.text)
        if api_matches:
            print(f"找到API端点: {api_matches[:3]}")
            
except Exception as e:
    print(f"错误: {e}")

# 方案3：尝试已知HKEX公告PDF格式
print("\n" + "=" * 60)
print("[方案3] 构造已知格式的HKEX PDF链接")
print("HKEX PDF链接格式: https://www1.hkexnews.hk/listedco/listconews/sehk/{年份}/{月}/{日}/{公告编号}.pdf")
print("\n示例（腾讯2024年年报）:")
example_pdf = "https://www1.hkexnews.hk/listedco/listconews/sehk/2025/03/28/2025032800005.pdf"
print(f"  {example_pdf}")

# 尝试访问
try:
    r = requests.head(example_pdf, headers=headers, timeout=10)
    print(f"  状态码: {r.status_code}")
    if r.status_code == 200:
        print(f"  文件大小: {int(r.headers.get('Content-Length', 0))//1024}KB")
except Exception as e:
    print(f"  错误: {e}")

# 方案4：AKShare港股公告接口
print("\n" + "=" * 60)
print("[方案4] AKShare港股公告接口")
try:
    import akshare as ak
    
    # 测试stock_hk_notice接口
    print("\n尝试stock_hk_notice接口:")
    try:
        df = ak.stock_hk_notice(symbol="00700")
        print(f"返回 {len(df)} 条公告")
        if len(df) > 0:
            print(f"列: {list(df.columns)}")
            # 查找年报
            annual = df[df['公告标题'].str.contains('年报|年度报告', na=False)]
            print(f"年报: {len(annual)} 条")
            for i, row in annual.head(3).iterrows():
                print(f"  - {row['公告日期']} | {row['公告标题']}")
                # 检查是否有链接
                if '链接' in row:
                    print(f"    链接: {row['链接']}")
    except Exception as e:
        print(f"stock_hk_notice失败: {e}")
    
    # 测试其他港股接口
    print("\n尝试stock_hk_news接口:")
    try:
        df2 = ak.stock_hk_news(symbol="00700")
        print(f"返回 {len(df2)} 条新闻")
        if len(df2) > 0:
            print(f"列: {list(df2.columns)}")
    except Exception as e:
        print(f"stock_hk_news失败: {e}")
        
except ImportError:
    print("AKShare未安装")

# 方案5：直接从公司IR页面获取
print("\n" + "=" * 60)
print("[方案5] 公司IR页面（手动推荐）")
print("""
腾讯IR页面: https://www.tencent.com/en-us/investors.html
阿里巴巴IR: https://ir.alibaba.com/
美团IR: https://ir.meituan.com/

这些页面通常有直接的年报PDF下载链接，适合手动下载后放入工作区处理。
""")

# 总结
print("\n" + "=" * 60)
print("港股PDF获取策略总结")
print("=" * 60)
print("""
方案对比：
┌─────────────────────────────────────────────────────┐
│ 方案            │ 可行性 │ 自动化 │ 备注           │
├─────────────────────────────────────────────────────┤
│ HKEX披露易搜索  │ ⚠️ SPA │ ❌     │ 需browser auto│
│ 东方财富港股API │ ❌ 失败│ ❌     │ API不存在     │
│ AKShare港股公告 │ ⚠️ 测试│ ⚠️     │ 需验证链接字段│
│ 已知公告编号构造│ ⚠️ 需ID│ ⚠️     │ 编号不易获取  │
│ 公司IR页面     │ ✅ 最稳│ ❌ 手动│ 推荐手动下载  │
└─────────────────────────────────────────────────────┘

推荐策略：
1. 港股财务数据：用AKShare（hk_financial.py已实现）
2. 港股年报PDF：手动从公司IR下载，放入工作区处理
3. 未来方案：配置browser automation后自动爬取HKEX
""")
