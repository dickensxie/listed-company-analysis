"""
配置模块：读取环境变量和本地配置文件
"""
import os
from pathlib import Path

# Token 文件路径（skill 目录下）
_TOKEN_FILE = Path(__file__).parent.parent / '.tushare_token'

def get_tushare_token() -> str:
    """获取 Tushare Token，优先级：环境变量 > 本地文件"""
    # 1. 尝试从环境变量读取
    token = os.environ.get('TUSHARE_TOKEN')
    if token and len(token) > 20:
        return token
    
    # 2. 尝试从本地文件读取
    if _TOKEN_FILE.exists():
        token = _TOKEN_FILE.read_text().strip()
        if token and len(token) > 20:
            # 同时设置环境变量，供后续代码使用
            os.environ['TUSHARE_TOKEN'] = token
            return token
    
    return None

# 启动时自动加载 token
TUSHARE_TOKEN = get_tushare_token()
