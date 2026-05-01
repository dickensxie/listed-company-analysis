# -*- coding: utf-8 -*-
"""
深交所互动易问答模块

功能：
- 获取公司问答列表
- 搜索特定问题
- 提取问答内容

数据源：AKShare stock_irm_cninfo() 接口（调用巨潮信息API）
替代方案：因互动易(irm.cninfo.com.cn)是全站Vue SPA，无公开API，故采用AKShare封装

测试：python szse_qa.py [股票代码]
"""

import warnings
warnings.filterwarnings('ignore')
import akshare as ak
from typing import List, Dict, Optional
import sys


def fetch_szse_qa(stock_code: str = None, keyword: str = None, limit: int = 20) -> List[Dict]:
    """
    获取深交所互动易问答
    
    Args:
        stock_code: 股票代码（如000001，支持A股代码）
        keyword: 搜索关键词
        limit: 返回条数
    
    Returns:
        问答列表，每项包含: question, answer, time, company, source
    """
    results = []
    
    try:
        # 使用AKShare接口（底层调用巨潮信息API）
        if stock_code:
            # 获取指定股票的问答
            df = ak.stock_irm_cninfo(stock=stock_code)
        elif keyword:
            # 搜索关键词
            df = ak.stock_irm_cninfo(stock="", query_key=keyword)
        else:
            # 获取最新问答（无股票代码无关键词，返回空）
            return []
        
        if df is not None and not df.empty:
            # 限制返回条数
            df = df.head(limit)
            
            for _, row in df.iterrows():
                qa = {
                    'question': str(row.get('提问', '')),
                    'answer': str(row.get('回答', '')),
                    'time': str(row.get('提问时间', '')),
                    'company': str(row.get('公司', '')),
                    'stock': str(row.get('股票代码', '')),
                    'source': '巨潮信息-互动易',
                }
                results.append(qa)
    
    except Exception as e:
        print(f"⚠️ 获取互动易问答失败: {e}")
        # 返回空列表，不影响主流程
        return []
    
    return results


def search_szse_qa(keyword: str, limit: int = 20) -> List[Dict]:
    """搜索互动易问答（关键词搜索）"""
    return fetch_szse_qa(keyword=keyword, limit=limit)


def get_company_qa(stock_code: str, limit: int = 20) -> List[Dict]:
    """获取公司互动易问答"""
    return fetch_szse_qa(stock_code=stock_code, limit=limit)


def format_qa_summary(qa_list: List[Dict]) -> str:
    """格式化问答为Markdown"""
    if not qa_list:
        return "暂无互动易问答数据"
    
    lines = []
    lines.append(f"## 互动易问答（{len(qa_list)}条）\n")
    
    for i, qa in enumerate(qa_list[:10], 1):
        lines.append(f"### {i}. {qa.get('question', '')[:50]}...")
        lines.append(f"- **公司**: {qa.get('company', '')} ({qa.get('stock', '')})")
        lines.append(f"- **时间**: {qa.get('time', '')}")
        answer = qa.get('answer', '')
        if answer:
            lines.append(f"- **回答**: {answer[:200]}{'...' if len(answer) > 200 else ''}")
        lines.append("")
    
    return "\n".join(lines)


# 便捷函数
def fetch_szse_qa_safe(stock_code: str = None, keyword: str = None, limit: int = 20, data_dir: str = None) -> Dict:
    """
    安全获取互动易问答（包装函数，返回标准格式）
    
    Returns:
        标准格式字典，包含 qa_list, count, warnings, findings
    """
    result = {
        'qa_list': [],
        'count': 0,
        'warnings': [],
        'findings': {},
    }
    
    try:
        qa_list = fetch_szse_qa(stock_code=stock_code, keyword=keyword, limit=limit)
        result['qa_list'] = qa_list
        result['count'] = len(qa_list)
        
        if not qa_list:
            result['warnings'].append('互动易无问答数据（AKShare接口可能限流）')
        
    except Exception as e:
        result['warnings'].append(f'互动易模块异常: {e}')
    
    # 保存原始数据
    if data_dir and qa_list:
        import os, json
        os.makedirs(data_dir, exist_ok=True)
        out = os.path.join(data_dir, 'szse_qa.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(qa_list, f, ensure_ascii=False, indent=2)
        result['findings']['raw_file'] = out
    
    return result


if __name__ == '__main__':
    print("=" * 70)
    print("深交所互动易模块测试（基于AKShare stock_irm_cninfo）")
    print("=" * 70)
    
    stock = sys.argv[1] if len(sys.argv) > 1 else '000001'
    print(f"\n测试股票: {stock}")
    
    # 测试获取公司问答
    print("\n### 获取公司问答...")
    qa_list = get_company_qa(stock, limit=5)
    print(f"获取到 {len(qa_list)} 条问答")
    
    if qa_list:
        print("\n前3条:")
        for i, qa in enumerate(qa_list[:3], 1):
            print(f"\n{i}. {qa.get('question', '')[:60]}...")
            print(f"   回答: {qa.get('answer', '')[:100]}...")
            print(f"   时间: {qa.get('time', '')}")
    
    # 测试搜索
    print("\n### 测试搜索...")
    search_results = search_szse_qa("分红", limit=3)
    print(f"搜索'分红'得到 {len(search_results)} 条")
    
    # 格式化输出
    print("\n### 格式化输出:")
    print(format_qa_summary(qa_list))
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
