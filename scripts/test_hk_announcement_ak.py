"""测试AKShare港股公告接口"""
import akshare as ak

# 测试港股公告接口
print('=== 测试 stock_hk_announcement_em ===')
try:
    df = ak.stock_hk_announcement_em(symbol='00700')
    print(f'返回条数: {len(df)}')
    if len(df) > 0:
        print(f'列名: {list(df.columns)}')
        print(df.head(3).to_string())
except Exception as e:
    print(f'错误: {e}')

# 测试其他港股新闻接口
print('\n=== 测试 stock_news_em ===')
try:
    df2 = ak.stock_news_em(symbol='00700')
    print(f'返回条数: {len(df2)}')
    if len(df2) > 0:
        print(f'列名: {list(df2.columns)}')
        print(df2.head(2).to_string())
except Exception as e:
    print(f'错误: {e}')

# 测试港股公告详情
print('\n=== 测试 stock_hk_announcement_detail_em ===')
try:
    # 先获取公告列表
    df_list = ak.stock_hk_announcement_em(symbol='00700')
    if len(df_list) > 0:
        # 尝试获取第一条详情
        print(f'公告列表样例:\n{df_list.head(1).to_string()}')
except Exception as e:
    print(f'错误: {e}')
