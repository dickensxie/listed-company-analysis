# -*- coding: utf-8 -*-
"""
上市公司全景分析 - 安装配置
"""
from setuptools import setup, find_packages

setup(
    name='listed-company-analysis',
    version='1.0.0',
    description='上市公司全景分析工具（A股+港股，15维度）',
    author='龙小新',
    python_requires='>=3.8',
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.0',
        'pandas>=1.3.0',
        'PyMuPDF>=1.23.0',
        'akshare>=1.12.0',
    ],
    extras_require={
        'full': [
            'pdfplumber>=0.10.0',
            'matplotlib>=3.5.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'company-analysis=analyze:main',
        ],
    },
)
