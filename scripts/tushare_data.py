# -*- coding: utf-8 -*-
"""
Tushare 数据封装模块
数据源: Tushare Pro API (https://tushare.pro)
功能: 分红送股(dividend)、解禁数据(share_float)、公司信息(company)

权限说明:
- 免费版Token(120积分/日): 可访问基础行情、分红、解禁、公司信息
- 权限不足: 财务三表、PE/PB估值、资金流向、概念板块

使用方法:
    from scripts.tushare_data import TushareData
    ts = TushareData()
    div = ts.get_dividend('000001.SZ')
    unlock = ts.get_share_float('000001.SZ')
"""
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Token配置（优先级：环境变量 > 本地文件）
_TOKEN_FILE = Path(__file__).parent.parent / '.tushare_token'

def _get_token():
    token = os.environ.get('TUSHARE_TOKEN')
    if not token and _TOKEN_FILE.exists():
        token = _TOKEN_FILE.read_text().strip()
    return token

TUSHARE_TOKEN = _get_token()

try:
    import tushare as ts
    if TUSHARE_TOKEN:
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        TUSHARE_OK = True
    else:
        TUSHARE_OK = False
        print("[WARN] Tushare Token未配置，请设置环境变量TUSHARE_TOKEN或创建.tushare_token文件")
except ImportError:
    TUSHARE_OK = False
    print("[WARN] Tushare未安装，请运行: pip install tushare")


class TushareData:
    """Tushare数据封装类"""
    
    def __init__(self):
        if not TUSHARE_OK:
            self.pro = None
        else:
            self.pro = pro
    
    def get_dividend(self, ts_code, years=10):
        """
        获取分红送股历史
        
        参数:
            ts_code: 股票代码，格式如'000001.SZ'/'600519.SH'/'00700.HK'
            years: 回溯年数，默认10年
        
        返回:
            {
                'success': True/False,
                'source': 'tushare_dividend',
                'data': [
                    {
                        'ann_date': '20260315',
                        'fiscal_year': '2025',
                        'div_type': '年度分配',
                        'cash_per_share': 0.3,
                        'bonus_ratio': 0.0,  # 每10股送股
                        'convert_ratio': 0.0,  # 每10股转增
                        'record_date': '20260420',
                        'ex_date': '20260421',
                        'pay_date': '20260421',
                        'total_dividend': 1000000000  # 分红总额(元)
                    },
                    ...
                ],
                'stats': {
                    'total_years': 10,
                    'dividend_years': 8,
                    'avg_cash_per_share': 0.25,
                    'total_cash': 8000000000
                }
            }
        """
        result = {
            'success': False,
            'source': 'tushare_dividend',
            'data': [],
            'stats': {},
            'error': None
        }
        
        if not self.pro:
            result['error'] = 'Tushare未初始化'
            return result
        
        try:
            # 计算起始年份
            start_year = datetime.now().year - years
            start_date = f"{start_year}0101"
            
            df = self.pro.dividend(
                ts_code=ts_code,
                start_date=start_date
                # 字段: end_date(期末), ann_date(公告日), div_proc(进度), stk_div(每股送股)
                # stk_bo_rate(每10股送), stk_co_rate(每10股转增), cash_div(每股现金), cash_div_tax(扣税后)
                # record_date(股权登记日), ex_date(除权除息日), pay_date(派息日)
            )
            
            if df is None or df.empty:
                result['error'] = '无分红记录'
                return result
            
            records = []
            total_cash = 0
            cash_values = []
            
            for _, row in df.iterrows():
                # Tushare实际字段名：end_date, cash_div(每股现金), stk_bo_rate(每10股送), stk_co_rate(每10股转)
                cash = float(row.get('cash_div') or 0)
                stk_bo = float(row.get('stk_bo_rate') or 0)  # 每10股送股
                stk_co = float(row.get('stk_co_rate') or 0)  # 每10股转增
                
                # 只统计已实施的分红（div_proc='实施'）
                div_proc = row.get('div_proc', '')
                
                records.append({
                    'end_date': str(row.get('end_date', '')),  # 期末（如20251231）
                    'ann_date': str(row.get('ann_date', '')),
                    'div_proc': div_proc,
                    'cash_per_share': cash,  # 每股现金分红（元）
                    'bonus_ratio': stk_bo,    # 每10股送股数
                    'convert_ratio': stk_co,  # 每10股转增数
                    'record_date': str(row.get('record_date', '')),
                    'ex_date': str(row.get('ex_date', '')),
                    'pay_date': str(row.get('pay_date', '')),
                    'cash_div_tax': float(row.get('cash_div_tax') or 0)  # 扣税后
                })
                
                # 只统计已实施且现金分红>0的记录
                if div_proc == '实施' and cash > 0:
                    cash_values.append(cash)
            
            result['success'] = True
            result['data'] = records
            # 过滤出已实施分红的记录
            implemented = [r for r in records if r['div_proc'] == '实施' and r['cash_per_share'] > 0]
            result['stats'] = {
                'total_records': len(records),
                'implemented_count': len(implemented),
                'avg_cash_per_share': sum(cash_values) / len(cash_values) if cash_values else 0,
                'latest_cash_per_share': implemented[0]['cash_per_share'] if implemented else 0,
                'dividend_years': len(set([r['end_date'][:4] for r in implemented]))
            }
            
        except Exception as e:
            err = str(e)
            if '权限' in err or '访问' in err:
                result['error'] = '权限不足：需要付费版本'
            else:
                result['error'] = f'API调用失败: {err[:80]}'
        
        return result
    
    def get_share_float(self, ts_code, days=365):
        """
        获取限售股解禁时间表
        
        参数:
            ts_code: 股票代码
            days: 未来天数，默认365天
        
        返回:
            {
                'success': True/False,
                'source': 'tushare_share_float',
                'data': [
                    {
                        'ann_date': '20260101',
                        'float_date': '20260415',
                        'float_share': 100000000,  # 解禁股数(股)
                        'float_ratio': 5.5,  # 占流通股比例%
                        'holder_name': 'XX投资',
                        'share_type': '定向增发'
                    },
                    ...
                ],
                'stats': {
                    'total_unlocks': 5,
                    'total_shares': 500000000,
                    'max_unlock_date': '20260415',
                    'max_unlock_ratio': 5.5
                }
            }
        """
        result = {
            'success': False,
            'source': 'tushare_share_float',
            'data': [],
            'stats': {},
            'error': None
        }
        
        if not self.pro:
            result['error'] = 'Tushare未初始化'
            return result
        
        try:
            # 计算日期范围
            start_date = datetime.now().strftime('%Y%m%d')
            end_date = (datetime.now() + timedelta(days=days)).strftime('%Y%m%d')
            
            df = self.pro.share_float(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,ann_date,float_date,float_share,float_ratio,holder_name,share_type'
            )
            
            if df is None or df.empty:
                # 无解禁不是error，是正常业务场景
                result['success'] = True
                result['data'] = []
                result['stats'] = {'total_unlocks': 0, 'total_shares': 0, 'note': '当前无解禁安排'}
                return result
            
            records = []
            total_shares = 0
            max_unlock = {'ratio': 0, 'date': ''}
            
            for _, row in df.iterrows():
                shares = float(row.get('float_share') or 0)
                ratio = float(row.get('float_ratio') or 0)
                
                records.append({
                    'ann_date': str(row.get('ann_date', '')),
                    'float_date': str(row.get('float_date', '')),
                    'float_share': shares,
                    'float_ratio': ratio,
                    'holder_name': row.get('holder_name', ''),
                    'share_type': row.get('share_type', '')
                })
                
                total_shares += shares
                if ratio > max_unlock['ratio']:
                    max_unlock = {'ratio': ratio, 'date': str(row.get('float_date', ''))}
            
            result['success'] = True
            result['data'] = records
            result['stats'] = {
                'total_unlocks': len(records),
                'total_shares': total_shares,
                'max_unlock_date': max_unlock['date'],
                'max_unlock_ratio': max_unlock['ratio']
            }
            
        except Exception as e:
            err = str(e)
            if '权限' in err or '访问' in err:
                result['error'] = '权限不足：需要付费版本'
            else:
                result['error'] = f'API调用失败: {err[:80]}'
        
        return result
    
    def get_company_info(self, ts_code):
        """
        获取公司基础信息（补充现有数据）
        
        返回:
            {
                'success': True/False,
                'source': 'tushare_company',
                'data': {
                    'ts_code': '000001.SZ',
                    'name': '平安银行',
                    'industry': '银行',
                    'market': '主板',
                    'list_date': '19910403',
                    'setup_date': '19871222',
                    'province': '广东',
                    'city': '深圳',
                    'chairman': 'XXX',
                    'main_business': '吸收存款、发放贷款...',
                    'website': 'http://...',
                    'employees': 35000
                }
            }
        """
        result = {
            'success': False,
            'source': 'tushare_company',
            'data': {},
            'error': None
        }
        
        if not self.pro:
            result['error'] = 'Tushare未初始化'
            return result
        
        try:
            df = self.pro.stock_company(ts_code=ts_code)
            
            if df is None or df.empty:
                result['error'] = '未找到公司信息'
                return result
            
            row = df.iloc[0]
            result['success'] = True
            result['data'] = {
                'ts_code': row.get('ts_code', ''),
                'name': row.get('chairman', ''),  # chairman字段实际是公司名
                'industry': row.get('industry', ''),
                'market': row.get('market', ''),
                'list_date': str(row.get('list_date', '')),
                'setup_date': str(row.get('setup_date', '')),
                'province': row.get('province', ''),
                'city': row.get('city', ''),
                'chairman': row.get('chairman', ''),
                'main_business': str(row.get('main_business', ''))[:200],
                'website': row.get('website', ''),
                'employees': int(row.get('employees') or 0)
            }
            
        except Exception as e:
            err = str(e)
            if '频率超限' in err:
                result['error'] = '频率限制：1次/小时（免费版）'
            elif '权限' in err:
                result['error'] = '权限不足'
            else:
                result['error'] = f'API调用失败: {err[:80]}'
        
        return result
    
    def get_daily(self, ts_code, start_date, end_date):
        """
        获取日线行情（补充/备用）
        
        参数:
            ts_code: 股票代码
            start_date: 起始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
        
        返回:
            {
                'success': True/False,
                'source': 'tushare_daily',
                'data': [...]
            }
        """
        result = {
            'success': False,
            'source': 'tushare_daily',
            'data': [],
            'error': None
        }
        
        if not self.pro:
            result['error'] = 'Tushare未初始化'
            return result
        
        try:
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                result['error'] = '无行情数据'
                return result
            
            records = df.to_dict('records')
            result['success'] = True
            result['data'] = records
            
        except Exception as e:
            result['error'] = str(e)[:80]
        
        return result


def _format_code(stock_code, market='a'):
    """
    将股票代码转换为Tushare格式
    
    参数:
        stock_code: 代码如'000001'/'600519'/'00700'
        market: 'a'(A股)/'hk'(港股)/'us'(美股)
    
    返回:
        '000001.SZ' / '600519.SH' / '00700.HK' / 'AAPL'
    """
    if market == 'us':
        return stock_code.upper()
    
    if market == 'hk':
        return f"{stock_code.zfill(5)}.HK"
    
    # A股市场
    code = stock_code.replace('.SH', '').replace('.SZ', '').replace('.BJ', '')
    
    if code[:2] in ['00', '30']:
        return f"{code}.SZ"
    elif code[:2] in ['60', '68']:
        return f"{code}.SH"
    elif code[0] in ['8', '4']:
        return f"{code}.BJ"
    else:
        return f"{code}.SZ"


# ===== CLI 入口 =====
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Tushare数据获取')
    parser.add_argument('--stock', '-s', required=True, help='股票代码')
    parser.add_argument('--market', '-m', default='a', choices=['a', 'hk', 'us'], help='市场')
    parser.add_argument('--dividend', '-d', action='store_true', help='获取分红数据')
    parser.add_argument('--float', '-f', action='store_true', help='获取解禁数据')
    parser.add_argument('--company', '-c', action='store_true', help='获取公司信息')
    parser.add_argument('--all', '-a', action='store_true', help='获取全部数据')
    parser.add_argument('--years', '-y', type=int, default=10, help='分红回溯年数')
    parser.add_argument('--days', type=int, default=365, help='解禁未来天数')
    
    args = parser.parse_args()
    
    ts = TushareData()
    ts_code = _format_code(args.stock, args.market)
    
    print(f"\n=== Tushare数据测试 ===")
    print(f"代码: {ts_code} ({args.market}市场)\n")
    
    if args.all or args.dividend:
        print("【分红送股】")
        div = ts.get_dividend(ts_code, args.years)
        if div['success']:
            print(f"✅ 共{len(div['data'])}条记录")
            for d in div['data'][:5]:
                cash = d.get('cash_per_share', 0)
                bonus = d.get('bonus_ratio', 0)
                print(f"  {d['fiscal_year']}: 现金{cash:.3f}元/股, 送股{bonus:.1f}")
            print(f"  统计: {div['stats']['dividend_years']}年分红, 平均{div['stats']['avg_cash_per_share']:.3f}元/股")
        else:
            print(f"❌ {div['error']}")
        print()
    
    if args.all or args.float:
        print("【解禁时间表】")
        unlock = ts.get_share_float(ts_code, args.days)
        if unlock['success']:
            print(f"✅ 共{len(unlock['data'])}次解禁")
            for u in unlock['data'][:5]:
                print(f"  {u['float_date']}: {u['float_share']:,.0f}股 ({u['float_ratio']:.2f}%), {u['share_type']}")
            print(f"  统计: 合计{unlock['stats']['total_shares']:,.0f}股, 最大单次{unlock['stats']['max_unlock_ratio']:.2f}%")
        else:
            print(f"❌ {unlock['error']}")
        print()
    
    if args.all or args.company:
        print("【公司信息】")
        info = ts.get_company_info(ts_code)
        if info['success']:
            d = info['data']
            print(f"✅ 行业: {d.get('industry', '?')}")
            print(f"   上市: {d.get('list_date', '?')}")
            print(f"   省份: {d.get('province', '?')}{d.get('city', '?')}")
            print(f"   员工: {d.get('employees', 0):,}人")
        else:
            print(f"❌ {info['error']}")
