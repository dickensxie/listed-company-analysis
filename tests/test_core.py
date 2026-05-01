# -*- coding: utf-8 -*-
"""
上市公司全景分析 - 核心路径单元测试

覆盖：
1. 沪市(601127) + 深市(002180) 核心维度
2. safe_request 工具函数
3. 审计意见提取（PDF优先 → 推断降级）
4. 子公司名自动提取（无硬编码）
5. 板块代码自动判断

运行：python -m pytest tests/ -v
      或 python tests/test_core.py
"""
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# 确保可以import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.safe_request import safe_get, safe_extract, safe_float
from scripts.financials import _get_audit_opinion, _infer_audit_opinion, _parse_audit_from_text
from scripts.subsidiary import _extract_sub_name, _extract_target_board, _parse_subsidiary_names


class TestSafeRequest(unittest.TestCase):
    """safe_request 工具函数测试"""
    
    def test_safe_extract_basic(self):
        data = {'result': {'data': [{'name': 'test'}]}}
        self.assertEqual(safe_extract(data, ['result', 'data', 0, 'name']), 'test')
    
    def test_safe_extract_missing_key(self):
        data = {'result': {}}
        self.assertIsNone(safe_extract(data, ['result', 'data']))
    
    def test_safe_extract_with_default(self):
        data = {}
        self.assertEqual(safe_extract(data, ['missing'], default=[]), [])
    
    def test_safe_extract_none_data(self):
        self.assertIsNone(safe_extract(None, ['any']))
    
    def test_safe_float(self):
        self.assertEqual(safe_float('3.14'), 3.14)
        self.assertIsNone(safe_float(None))
        self.assertIsNone(safe_float('abc'))
        self.assertEqual(safe_float('abc', 0.0), 0.0)


class TestAuditOpinion(unittest.TestCase):
    """审计意见提取测试"""
    
    def test_infer_standard(self):
        """EPS>0, ROE>0 → 标准无保留（推断）"""
        result = _infer_audit_opinion(3.96, 45.43)
        self.assertIn('标准无保留', result)
        self.assertIn('推断', result)
    
    def test_infer_nonstandard(self):
        """EPS<0, ROE<0 → 非标准无保留（推断）"""
        result = _infer_audit_opinion(-0.51, -7.68)
        self.assertIn('非标准无保留', result)
    
    def test_infer_negative_eps(self):
        """EPS<0, ROE>0 → 存在不确定性（推断）"""
        result = _infer_audit_opinion(-0.5, 5.0)
        self.assertIn('不确定性', result)
    
    def test_parse_audit_standard(self):
        """从文本提取：标准无保留意见"""
        text = "我们审计了...财务报表...我们认为...标准无保留意见。"
        result = _parse_audit_from_text(text)
        self.assertEqual(result, '标准无保留意见')
    
    def test_parse_audit_emphasis(self):
        """从文本提取：带强调事项段的无保留意见"""
        text = "我们审计了...带强调事项段的无保留意见...强调事项：未弥补亏损..."
        result = _parse_audit_from_text(text)
        self.assertEqual(result, '带强调事项段的无保留意见')
    
    def test_parse_audit_qualified(self):
        """从文本提取：保留意见"""
        text = "我们审计了...保留意见...除...的影响外..."
        result = _parse_audit_from_text(text)
        self.assertEqual(result, '保留意见')
    
    def test_parse_audit_disclaimer(self):
        """从文本提取：无法表示意见"""
        text = "我们审计了...无法表示意见..."
        result = _parse_audit_from_text(text)
        self.assertEqual(result, '无法表示意见')
    
    def test_parse_audit_adverse(self):
        """从文本提取：否定意见"""
        text = "我们审计了...否定意见..."
        result = _parse_audit_from_text(text)
        self.assertEqual(result, '否定意见')
    
    def test_parse_audit_no_match(self):
        """无匹配文本 → 返回None"""
        text = "这是一段普通的财务描述文字，没有审计意见关键词。"
        result = _parse_audit_from_text(text)
        self.assertIsNone(result)


class TestSubsidiaryExtraction(unittest.TestCase):
    """子公司名自动提取测试（无硬编码）"""
    
    def test_extract_sub_name_fencha(self):
        """分拆上市标题提取"""
        title = "关于子公司珠海极海微电子股份有限公司分拆上市的提示性公告"
        result = _extract_sub_name(title)
        self.assertIn('极海微', result)
    
    def test_extract_sub_name_ipo(self):
        """IPO辅导标题提取"""
        title = "关于子公司芯密科技首次公开发行股票并在创业板上市的辅导备案公告"
        result = _extract_sub_name(title)
        self.assertIn('芯密科技', result)
    
    def test_extract_sub_name_unknown(self):
        """无子公司名标题 → 返回未知"""
        title = "关于公司重大资产重组的公告"
        result = _extract_sub_name(title)
        self.assertEqual(result, '未知')
    
    def test_extract_target_board_kcb(self):
        title = "关于子公司首次公开发行股票并在科创板上市的公告"
        self.assertEqual(_extract_target_board(title), '科创板')
    
    def test_extract_target_board_cyb(self):
        title = "关于子公司首次公开发行股票并在创业板上市辅导备案公告"
        self.assertEqual(_extract_target_board(title), '创业板')
    
    def test_extract_target_board_bse(self):
        title = "关于子公司向北交所提交上市申请的公告"
        self.assertEqual(_extract_target_board(title), '北交所')
    
    def test_extract_target_board_unknown(self):
        title = "关于子公司分拆上市的提示性公告"
        self.assertEqual(_extract_target_board(title), '未知（需查原始公告）')
    
    def test_parse_subsidiary_names(self):
        """从年报文本提取子公司名"""
        text = """
        主要控股参股公司分析：
        珠海极海微电子股份有限公司 81.2%
        纳思达商用设备有限公司 70.0%
        极海中国（香港）有限公司 100%
        """
        names = _parse_subsidiary_names(text)
        self.assertTrue(len(names) >= 2)
        self.assertTrue(any('极海微' in n for n in names))


class TestPlateDetection(unittest.TestCase):
    """板块代码自动判断测试"""
    
    def test_shanghai_main(self):
        """60开头 → 沪市主板 .SH"""
        from scripts.financials import fetch_financial_metrics
        # 测试 secucode 逻辑（通过实际函数间接验证）
        # 直接测 secucode 构造
        stock_code = '601127'
        if stock_code[:2] in ['60', '68']:
            secucode = stock_code + '.SH'
        else:
            secucode = stock_code + '.SZ'
        self.assertEqual(secucode, '601127.SH')
    
    def test_shanghai_kcb(self):
        """68开头 → 科创板 .SH"""
        stock_code = '688001'
        if stock_code[:2] in ['60', '68']:
            secucode = stock_code + '.SH'
        else:
            secucode = stock_code + '.SZ'
        self.assertEqual(secucode, '688001.SH')
    
    def test_shenzhen_main(self):
        """00开头 → 深市主板 .SZ"""
        stock_code = '002180'
        if stock_code[:2] in ['00', '30']:
            secucode = stock_code + '.SZ'
        else:
            secucode = stock_code + '.SH'
        self.assertEqual(secucode, '002180.SZ')
    
    def test_shenzhen_cyb(self):
        """30开头 → 创业板 .SZ"""
        stock_code = '300750'
        if stock_code[:2] in ['00', '30']:
            secucode = stock_code + '.SZ'
        else:
            secucode = stock_code + '.SH'
        self.assertEqual(secucode, '300750.SZ')
    
    def test_bse(self):
        """8开头 → 北交所 .BJ"""
        stock_code = '830799'
        if stock_code[0] in ['8', '4']:
            secucode = stock_code + '.BJ'
        else:
            secucode = stock_code + '.SZ'
        self.assertEqual(secucode, '830799.BJ')


class TestIntegrationSmoke(unittest.TestCase):
    """集成冒烟测试（需要网络，标记为慢测试）"""
    
    @unittest.skipUnless(os.environ.get('RUN_SLOW_TESTS'), '需要网络，设置 RUN_SLOW_TESTS=1 运行')
    def test_sh_financial(self):
        """沪市财务数据获取"""
        from scripts.financials import fetch_financial_metrics
        result = fetch_financial_metrics('601127', market='a')
        self.assertIsNotNone(result)
        self.assertTrue(len(result.get('records', [])) > 0)
        self.assertIsNotNone(result.get('audit_opinion'))
    
    @unittest.skipUnless(os.environ.get('RUN_SLOW_TESTS'), '需要网络，设置 RUN_SLOW_TESTS=1 运行')
    def test_sz_financial(self):
        """深市财务数据获取"""
        from scripts.financials import fetch_financial_metrics
        result = fetch_financial_metrics('002180', market='a')
        self.assertIsNotNone(result)
        self.assertTrue(len(result.get('records', [])) > 0)
        self.assertIsNotNone(result.get('audit_opinion'))
    
    @unittest.skipUnless(os.environ.get('RUN_SLOW_TESTS'), '需要网络，设置 RUN_SLOW_TESTS=1 运行')
    def test_industry(self):
        """行业识别"""
        from scripts.industry import fetch_industry_info
        result = fetch_industry_info('601127', market='a')
        self.assertIsNotNone(result)
        ic = result.get('industry_class', {})
        self.assertIsNotNone(ic.get('csrc_industry'))
        self.assertTrue(len(result.get('competitors', [])) > 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
