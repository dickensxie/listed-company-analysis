# -*- coding: utf-8 -*-
"""
上证e互动问答提取模块（修正版）

发现：API返回HTML片段，非JSON
正确端点：ajax/feeds.do?type=11&page=1&pageSize=10
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, List, Optional

# 请求头
SSE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html, */*',
    'X-Requested-With': 'XMLHttpRequest',
}

SSE_BASE_URL = 'https://sns.sseinfo.com'


class SSEInfoAPI:
    """上证e互动API封装"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SSE_HEADERS)
        self.last_request_time = 0
    
    def _rate_limit(self):
        """请求间隔控制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self.last_request_time = time.time()
    
    def _get(self, url: str, params: Dict = None) -> Optional[BeautifulSoup]:
        """GET请求封装"""
        self._rate_limit()
        try:
            r = self.session.get(url, params=params, timeout=15)
            r.encoding = 'utf-8'
            if r.status_code == 200:
                return BeautifulSoup(r.text, 'html.parser')
            else:
                print(f"请求失败: {r.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    def _parse_feed_item(self, item) -> Optional[Dict]:
        """解析单条问答或问题
        
        支持两种结构：
        1. Q&A结构（type=11）: m_qa_detail + m_qa
        2. 问题结构（type=10）: m_feed_detail（无回答）
        """
        try:
            qa = {}
            
            # 获取item ID
            item_id = item.get('id', '')
            if item_id:
                qa['id'] = item_id.replace('item-', '')
            
            # 检查是问答结构还是问题结构
            is_qa = 'm_qa' in item.get('class', []) or item.find('div', class_='m_qa') is not None
            
            # 问题内容 - 优先检查m_qa_detail（问答），否则用m_feed_detail（问题）
            question_elem = item.find('div', class_='m_qa_detail')
            if not question_elem:
                question_elem = item.find('div', class_='m_feed_detail')
            
            if question_elem:
                question_text = question_elem.find('div', class_='m_feed_txt')
                if question_text:
                    # 先提取公司名（从链接）
                    company_link = question_text.find('a')
                    if company_link:
                        link_text = company_link.get_text(strip=True)
                        # 格式: ":万润新能(688275)" 或 "万润新能(688275)"
                        if link_text and link_text.startswith(':'):
                            link_text = link_text[1:]
                        if '(' in link_text:
                            qa['company'] = link_text.split('(')[0]
                    # 提取纯文本，移除公司链接
                    for a in question_text.find_all('a'):
                        a.decompose()
                    qa['question'] = question_text.get_text(strip=True)
                
                # 提取公司信息（从问题文本链接或头像区）
                # 方式1：从头像区
                face = question_elem.find('div', class_='m_feed_face')
                if face:
                    p = face.find('p')
                    if p and '投资者' not in p.get_text():
                        qa['company'] = p.get_text(strip=True)
            
            # 回答内容 - m_qa区块（仅问答结构有）
            answer_elem = item.find('div', class_='m_qa')
            if answer_elem:
                answer_text = answer_elem.find('div', class_='m_feed_txt')
                if answer_text:
                    qa['answer'] = answer_text.get_text(strip=True)
                
                # 提取回答方（公司）
                ans_face = answer_elem.find('div', class_='m_feed_face')
                if ans_face:
                    ans_company = ans_face.find('p')
                    if ans_company:
                        qa['company'] = ans_company.get_text(strip=True)
            
            # 时间
            time_elem = item.find('div', class_='m_feed_from')
            if time_elem:
                time_span = time_elem.find('span')
                if time_span:
                    qa['time'] = time_span.get_text(strip=True)
            
            return qa if qa.get('question') or qa.get('answer') else None
            
        except Exception as e:
            return None
    
    def get_latest_qa(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """获取最新问答列表
        
        Args:
            page: 页码
            page_size: 每页条数
        
        Returns:
            问答列表
        """
        url = f'{SSE_BASE_URL}/ajax/feeds.do'
        params = {
            'type': 11,  # 11=最新问答
            'page': page,
            'pageSize': page_size,
            'lastid': -1,
            'show': ''
        }
        
        soup = self._get(url, params)
        if not soup:
            return []
        
        # 查找问答项
        items = soup.find_all('div', class_='m_feed_item')
        results = []
        for item in items:
            qa = self._parse_feed_item(item)
            if qa:
                results.append(qa)
        
        return results
    
    def get_hot_qa(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """获取热门问答
        
        注意：需要完整参数，否则返回500错误
        """
        url = f'{SSE_BASE_URL}/ajax/feeds.do'
        params = {
            'page': page,
            'type': 10,  # 10=热门问答
            'pageSize': page_size,
            'lastid': -1,
            'show': ''
        }
        
        soup = self._get(url, params)
        if not soup:
            return []
        
        items = soup.find_all('div', class_='m_feed_item')
        results = []
        for item in items:
            qa = self._parse_feed_item(item)
            if qa:
                results.append(qa)
        
        return results
    
    def search_qa(self, keyword: str = None, company: str = None,
                  start_date: str = None, end_date: str = None,
                  page: int = 1, page_size: int = 20) -> List[Dict]:
        """搜索问答
        
        Args:
            keyword: 关键词
            company: 公司代码或名称
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            page: 页码
        """
        url = f'{SSE_BASE_URL}/ajax/feeds.do'
        params = {
            'type': 11,
            'page': page,
            'pageSize': page_size,
            'lastid': -1,
            'show': ''
        }
        
        if keyword:
            params['keyword'] = keyword
        if company:
            params['company'] = company
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        
        soup = self._get(url, params)
        if not soup:
            return []
        
        items = soup.find_all('div', class_='m_feed_item')
        results = []
        for item in items:
            qa = self._parse_feed_item(item)
            if qa:
                results.append(qa)
        
        return results
    
    def get_company_qa(self, company_id: str, page: int = 1, page_size: int = 20) -> List[Dict]:
        """获取公司问答（需要company_id，非股票代码）
        
        Args:
            company_id: 公司ID（如154587是茅台）
            page: 页码
            page_size: 每页条数
        """
        # 先获取公司页面确定company_id
        # 这里需要根据股票代码查找company_id
        # 暂时返回最新问答，后续可改进
        return self.search_qa(company=company_id, page=page)[:page_size]


# 便捷函数
_api = None

def get_api() -> SSEInfoAPI:
    global _api
    if _api is None:
        _api = SSEInfoAPI()
    return _api

def get_sse_latest_qa(limit: int = 20) -> List[Dict]:
    """获取上证e互动最新问答"""
    api = get_api()
    return api.get_latest_qa(page_size=limit)

def get_sse_hot_qa(limit: int = 20) -> List[Dict]:
    """获取上证e互动热门问答"""
    api = get_api()
    return api.get_hot_qa(page_size=limit)

def search_sse_qa(keyword: str, limit: int = 20) -> List[Dict]:
    """搜索上证e互动问答"""
    api = get_api()
    return api.search_qa(keyword=keyword)[:limit]


# 测试代码
if __name__ == '__main__':
    print("=" * 70)
    print("上证e互动 API 测试")
    print("=" * 70)
    
    api = SSEInfoAPI()
    
    # 测试最新问答
    print("\n### 测试最新问答")
    qa_list = api.get_latest_qa(page_size=10)
    print(f"找到 {len(qa_list)} 条问答")
    for i, qa in enumerate(qa_list[:5], 1):
        print(f"\n{i}. [{qa.get('company', '')}] {qa.get('time', '')}")
        q = qa.get('question', '')
        print(f"   问: {q[:80]}..." if len(q) > 80 else f"   问: {q}")
        a = qa.get('answer', '')
        if a:
            print(f"   答: {a[:80]}..." if len(a) > 80 else f"   答: {a}")
    
    # 测试热门问答
    print("\n\n### 测试热门问答")
    hot_qa = api.get_hot_qa(page_size=5)
    print(f"找到 {len(hot_qa)} 条问答")
    for i, qa in enumerate(hot_qa[:3], 1):
        print(f"{i}. [{qa.get('company', '')}] {qa.get('question', '')[:50]}...")
    
    # 测试关键词搜索
    print("\n\n### 测试关键词搜索'茅台'")
    search_result = api.search_qa(keyword='茅台', page_size=5)
    print(f"找到 {len(search_result)} 条相关问答")
    for qa in search_result[:3]:
        print(f"  - [{qa.get('company', '')}] {qa.get('question', '')[:40]}...")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
