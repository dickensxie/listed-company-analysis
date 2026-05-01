"""探索AKShare港股相关接口"""
import akshare as ak

# 列出所有港股相关函数
print('=== AKShare港股相关函数 ===\n')
hk_funcs = [f for f in dir(ak) if 'hk' in f.lower() or 'hong' in f.lower()]
for f in sorted(hk_funcs):
    print(f)

# 测试可用的港股接口
print('\n\n=== 测试港股接口 ===\n')

test_funcs = [
    ('stock_hk_spot_em', [], '港股实时行情'),
    ('stock_hk_daily_em', ['00700'], '港股日线'),
    ('stock_hk_ggt_components_em', [], '港股通成分'),
]

for func_name, args, desc in test_funcs:
    print(f'--- {func_name} ({desc}) ---')
    try:
        func = getattr(ak, func_name)
        if args:
            df = func(*args)
        else:
            df = func()
        print(f'返回条数: {len(df)}')
        if len(df) > 0:
            print(f'列名: {list(df.columns)[:8]}')
            print(df.head(2).to_string())
    except Exception as e:
        print(f'错误: {e}')
    print()

# 尝试东方财富港股公告（非AKShare）
print('=== 尝试东方财富港股公告API ===\n')
import requests

headers = {'User-Agent': 'Mozilla/5.0'}
# 东方财富港股公告API（猜测格式）
em_apis = [
    'https://emweb.eastmoney.com/PC_HKF10/Notice/PageAjax?code=00700',
    'https://emweb.eastmoney.com/api/PC_HKF10/Notice/PageAjax?code=00700',
    'https://datacenter.eastmoney.com/api/data/v1/get?callback=jQuery&reportName=RPT_HKF10_NOTICE&columns=ALL&filter=(SECUCODE="00700")',
]

for api in em_apis:
    try:
        r = requests.get(api, headers=headers, timeout=5)
        print(f'{api}')
        print(f'  状态: {r.status_code}, 长度: {len(r.text)}')
        if r.status_code == 200 and len(r.text) > 50:
            print(f'  内容预览: {r.text[:200]}...')
    except Exception as e:
        print(f'  错误: {e}')
    print()
