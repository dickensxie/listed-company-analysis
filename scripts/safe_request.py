# -*- coding: utf-8 -*-
"""
通用工具：统一HTTP请求 + 降级处理

所有模块统一使用 safe_get() 替代 requests.get()，
自动处理：超时、重试、空数据、API变更。
"""
import requests
import time
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 默认请求头
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/html, */*',
}

# 默认超时（秒）
DEFAULT_TIMEOUT = 20

# 最大重试次数
MAX_RETRIES = 2

# 重试间隔（秒）
RETRY_DELAY = 1.5


def safe_get(url, params=None, headers=None, timeout=None, 
             retries=MAX_RETRIES, retry_delay=RETRY_DELAY,
             backoff=None, expect_json=True, encoding='utf-8'):
    """
    安全的HTTP GET请求，带重试和降级处理
    
    Args:
        url: 请求URL
        params: 查询参数
        headers: 自定义请求头（合并DEFAULT_HEADERS）
        timeout: 超时秒数
        retries: 重试次数
        retry_delay: 重试间隔
        expect_json: 是否期望JSON响应
        encoding: 响应编码
    
    Returns:
        dict/list/str: 解析后的响应数据
        None: 请求失败
    
    Raises:
        不抛出异常，所有错误降级为返回None + 打印警告
    """
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    timeout = timeout or DEFAULT_TIMEOUT
    # backoff 兼容：如果传了backoff，用作retry_delay
    if backoff is not None:
        retry_delay = backoff
    
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers=merged_headers, 
                           timeout=timeout)
            r.encoding = encoding
            
            if r.status_code != 200:
                if attempt < retries:
                    time.sleep(retry_delay)
                    continue
                return None
            
            if expect_json:
                try:
                    return r.json()
                except ValueError:
                    # 不是JSON，可能API变更
                    if attempt < retries:
                        time.sleep(retry_delay)
                        continue
                    return None
            else:
                return r.text
                
        except requests.Timeout:
            print(f"  ⚠️ 请求超时: {url[:60]}...")
            if attempt < retries:
                time.sleep(retry_delay)
                continue
            return None
            
        except requests.ConnectionError:
            print(f"  ⚠️ 连接失败: {url[:60]}...")
            if attempt < retries:
                time.sleep(retry_delay)
                continue
            return None
            
        except Exception as e:
            print(f"  ⚠️ 请求异常: {e}")
            if attempt < retries:
                time.sleep(retry_delay)
                continue
            return None
    
    return None


def safe_extract(data, path, default=None):
    """
    安全地从嵌套dict/list中提取值
    
    Args:
        data: 嵌套数据结构
        path: 路径列表，如 ['result', 'data', 0, 'name']
        default: 找不到时的默认值
    
    Returns:
        找到的值或default
    """
    current = data
    for key in path:
        if current is None:
            return default
        if isinstance(key, int) and isinstance(current, list):
            if key < len(current):
                current = current[key]
            else:
                return default
        elif isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current if current is not None else default


def safe_float(value, default=None):
    """安全转换为float"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=None):
    """安全转换为int"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_post(url, json=None, data=None, headers=None, timeout=None,
              retries=MAX_RETRIES, retry_delay=RETRY_DELAY,
              expect_json=True, encoding='utf-8'):
    """
    安全的HTTP POST请求，带重试和降级处理
    
    Args:
        url: 请求URL
        json: JSON请求体
        data: 表单数据（dict或str）
        headers: 自定义请求头
        timeout: 超时秒数
        retries: 重试次数
        expect_json: 是否期望JSON响应
        encoding: 响应编码
    
    Returns:
        requests.Response 对象（调用方自行处理）
        None: 请求失败
    """
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    timeout = timeout or DEFAULT_TIMEOUT
    
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, json=json, data=data,
                            headers=merged_headers, timeout=timeout)
            r.encoding = encoding
            return r
        except requests.Timeout:
            print(f"  ⚠️ POST超时: {url[:60]}...")
            if attempt < retries:
                time.sleep(retry_delay)
                continue
            return None
        except requests.ConnectionError:
            print(f"  ⚠️ POST连接失败: {url[:60]}...")
            if attempt < retries:
                time.sleep(retry_delay)
                continue
            return None
        except Exception as e:
            print(f"  ⚠️ POST异常: {e}")
            if attempt < retries:
                time.sleep(retry_delay)
                continue
            return None
    return None
