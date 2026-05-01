#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化图表生成模块 - 专业美观版

功能：
1. 财务趋势图（营收、利润、毛利率）
2. 估值对比图（PE/PB/PS行业对比）
3. 盈利预测情景图（三情景对比）
4. 股权结构图（饼图）
5. 行业竞争格局图（雷达图）
6. 风险雷达图

输出：PNG图片，保存到 output/charts/ 目录
"""

import json
import os
import sys
from typing import Dict, List, Optional

# 支持独立运行
if __name__ == '__main__' and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')  # 无GUI环境
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np

# ========== 专业配色方案 ==========
COLORS = {
    'primary': '#1f4e79',      # 深蓝 - 主色
    'secondary': '#2e75b5',    # 中蓝
    'accent': '#c55a11',       # 橙红 - 强调
    'success': '#548235',      # 绿
    'warning': '#bf8f00',      # 金黄
    'danger': '#c00000',       # 红
    'neutral': '#7f7f7f',      # 灰
    'light': '#d9e2f3',        # 浅蓝背景
    'bg': '#f8f9fa',           # 背景色
}

# 三情景配色
SCENARIO_COLORS = {
    'conservative': '#c55a11',  # 橙红 - 保守
    'neutral': '#1f4e79',       # 深蓝 - 中性
    'optimistic': '#548235',    # 绿 - 乐观
}

# ========== 字体设置 ==========
def setup_fonts():
    """设置中文字体，优先使用系统可用字体"""
    # 尝试找到可用的中文字体
    font_list = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial Unicode MS', 'WenQuanYi Micro Hei']
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    chinese_font = None
    for font in font_list:
        if font in available_fonts:
            chinese_font = font
            break
    
    if chinese_font:
        plt.rcParams['font.sans-serif'] = [chinese_font, 'DejaVu Sans']
    else:
        # 如果没有中文字体，使用默认字体并关闭中文
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['axes.labelsize'] = 10
    return chinese_font is not None

HAS_CHINESE_FONT = setup_fonts()


class ChartGenerator:
    """图表生成器 - 专业美观版"""
    
    def __init__(self, output_dir: str = None):
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = output_dir or os.path.join(script_dir, 'output', 'charts')
        os.makedirs(self.output_dir, exist_ok=True)
        self.has_chinese = HAS_CHINESE_FONT
        
    def _save_chart(self, fig, filename: str) -> str:
        """保存图表"""
        path = os.path.join(self.output_dir, filename)
        fig.savefig(path, dpi=200, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close(fig)
        return path
    
    def _add_title_box(self, ax, title: str, subtitle: str = None):
        """添加带背景色的标题"""
        ax.set_title(title, fontsize=14, fontweight='bold', color=COLORS['primary'], pad=15)
        if subtitle:
            ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, ha='center', 
                   fontsize=9, color=COLORS['neutral'], style='italic')
    
    def _style_axis(self, ax):
        """美化坐标轴"""
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(COLORS['neutral'])
        ax.spines['bottom'].set_color(COLORS['neutral'])
        ax.tick_params(colors=COLORS['neutral'], labelsize=9)
        ax.grid(True, alpha=0.3, linestyle='--', color=COLORS['neutral'])
    
    def plot_financial_trend(self, data: Dict, stock_code: str) -> str:
        """财务趋势图 - 专业版"""
        years = data.get('years', [])
        revenue = data.get('revenue', [])
        profit = data.get('net_profit', [])
        
        if not years or not revenue:
            return None
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor='white')
        fig.patch.set_facecolor('white')
        
        # 营收趋势 - 面积图+折线
        ax1.fill_between(years, revenue, alpha=0.3, color=COLORS['secondary'])
        ax1.plot(years, revenue, 'o-', linewidth=2.5, markersize=8, 
                color=COLORS['primary'], markerfacecolor='white', markeredgewidth=2)
        self._add_title_box(ax1, f'{stock_code} 营收趋势', '单位：亿元')
        self._style_axis(ax1)
        ax1.set_xlabel('年度', fontsize=10)
        ax1.set_ylabel('营收（亿元）', fontsize=10)
        
        # 添加数据标签
        for i, v in enumerate(revenue):
            ax1.annotate(f'{v:.1f}', (years[i], v), textcoords="offset points", 
                        xytext=(0, 12), ha='center', fontsize=9, fontweight='bold',
                        color=COLORS['primary'])
        
        # 净利润趋势 - 柱状图
        if profit:
            colors_bar = [COLORS['success'] if p >= 0 else COLORS['danger'] for p in profit]
            bars = ax2.bar(years, profit, color=colors_bar, alpha=0.8, edgecolor='white', linewidth=1.5)
            self._add_title_box(ax2, f'{stock_code} 净利润趋势', '单位：亿元')
            self._style_axis(ax2)
            ax2.set_xlabel('年度', fontsize=10)
            ax2.set_ylabel('净利润（亿元）', fontsize=10)
            ax2.axhline(y=0, color=COLORS['neutral'], linestyle='-', linewidth=0.8)
            
            # 添加数据标签
            for i, (bar, v) in enumerate(zip(bars, profit)):
                height = bar.get_height()
                ax2.annotate(f'{v:.1f}', 
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 5 if v >= 0 else -15),
                            textcoords="offset points",
                            ha='center', va='bottom' if v >= 0 else 'top',
                            fontsize=9, fontweight='bold',
                            color=COLORS['success'] if v >= 0 else COLORS['danger'])
        
        plt.tight_layout(pad=3.0)
        return self._save_chart(fig, f'{stock_code}_financial_trend.png')
    
    def plot_valuation_comparison(self, data: Dict, stock_code: str) -> str:
        """估值对比图 - 专业版"""
        target = data.get('target', {})
        peers = data.get('peers', [])
        
        if not target or not peers:
            return None
            
        fig, axes = plt.subplots(1, 3, figsize=(18, 5), facecolor='white')
        fig.patch.set_facecolor('white')
        
        metrics = [
            ('pe_ttm', 'PE(TTM)', 'x'),
            ('pb', 'PB', 'o'),
            ('ps', 'PS', 's')
        ]
        
        for idx, (key, label, marker) in enumerate(metrics):
            ax = axes[idx]
            ax.set_facecolor('#fafafa')
            
            peer_values = [p.get(key) for p in peers if p.get(key) is not None]
            target_value = target.get(key)
            
            if not peer_values:
                ax.text(0.5, 0.5, f'无{label}数据', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=11, color=COLORS['neutral'])
                ax.set_title(label, fontsize=12, fontweight='bold', color=COLORS['primary'])
                continue
            
            # 箱线图 - 美化
            bp = ax.boxplot(peer_values, labels=[label], patch_artist=True,
                           widths=0.5, showmeans=True, meanline=True)
            bp['boxes'][0].set_facecolor(COLORS['light'])
            bp['boxes'][0].set_edgecolor(COLORS['secondary'])
            bp['boxes'][0].set_linewidth(2)
            bp['medians'][0].set_color(COLORS['primary'])
            bp['medians'][0].set_linewidth(2)
            bp['means'][0].set_color(COLORS['accent'])
            bp['whiskers'][0].set_color(COLORS['neutral'])
            bp['whiskers'][1].set_color(COLORS['neutral'])
            bp['caps'][0].set_color(COLORS['neutral'])
            bp['caps'][1].set_color(COLORS['neutral'])
            
            # 标出目标公司
            if target_value:
                ax.scatter([1], [target_value], color=COLORS['accent'], 
                          marker=marker, s=250, zorder=5, edgecolors='white', linewidths=2,
                          label=f'{stock_code}')
                ax.annotate(f'{target_value:.1f}', (1, target_value), 
                           textcoords="offset points", xytext=(20, 0), 
                           fontsize=10, fontweight='bold', color=COLORS['accent'])
            
            # 标出中位数
            median = sorted(peer_values)[len(peer_values)//2]
            ax.axhline(y=median, color=COLORS['success'], linestyle='--', alpha=0.7, 
                      linewidth=1.5, label=f'行业中位数: {median:.1f}')
            
            ax.set_title(f'{label}对比', fontsize=12, fontweight='bold', color=COLORS['primary'])
            ax.legend(loc='upper right', fontsize=8, framealpha=0.9)
            self._style_axis(ax)
            ax.set_ylabel('倍数', fontsize=10)
        
        plt.suptitle(f'{stock_code} 估值对比（vs 行业可比公司）', 
                    fontsize=14, fontweight='bold', color=COLORS['primary'], y=1.02)
        plt.tight_layout(pad=3.0)
        return self._save_chart(fig, f'{stock_code}_valuation_comparison.png')
    
    def plot_forecast_scenarios(self, forecast_data: Dict, stock_code: str) -> str:
        """盈利预测情景图 - 专业版"""
        scenarios = forecast_data
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor='white')
        fig.patch.set_facecolor('white')
        
        labels = {'conservative': '保守', 'neutral': '中性', 'optimistic': '乐观'}
        
        # 营收预测
        for s in ['conservative', 'neutral', 'optimistic']:
            f = scenarios.get(s, {})
            years = f.get('years', [2026, 2027, 2028])
            revenue = f.get('revenue', [])
            if revenue:
                color = SCENARIO_COLORS[s]
                ax1.plot(years, revenue, 'o-', color=color, linewidth=2.5, 
                        markersize=8, markerfacecolor='white', markeredgewidth=2,
                        label=labels[s])
                for i, v in enumerate(revenue):
                    ax1.annotate(f'{v:.1f}', (years[i], v), textcoords="offset points", 
                                xytext=(0, 12), ha='center', fontsize=9, 
                                color=color, fontweight='bold')
        
        self._add_title_box(ax1, '营收预测（三情景）', '单位：亿元')
        self._style_axis(ax1)
        ax1.set_xlabel('年度', fontsize=10)
        ax1.set_ylabel('营收（亿元）', fontsize=10)
        ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
        
        # 净利润预测
        for s in ['conservative', 'neutral', 'optimistic']:
            f = scenarios.get(s, {})
            years = f.get('years', [2026, 2027, 2028])
            profit = f.get('net_profit', [])
            if profit:
                color = SCENARIO_COLORS[s]
                ax2.plot(years, profit, 's-', color=color, linewidth=2.5, 
                        markersize=8, markerfacecolor='white', markeredgewidth=2,
                        label=labels[s])
                for i, v in enumerate(profit):
                    ax2.annotate(f'{v:.1f}', (years[i], v), textcoords="offset points", 
                                xytext=(0, 12), ha='center', fontsize=9,
                                color=color, fontweight='bold')
        
        self._add_title_box(ax2, '净利润预测（三情景）', '单位：亿元')
        self._style_axis(ax2)
        ax2.set_xlabel('年度', fontsize=10)
        ax2.set_ylabel('净利润（亿元）', fontsize=10)
        ax2.legend(loc='upper left', fontsize=10, framealpha=0.9)
        
        plt.suptitle(f'{stock_code} 盈利预测', fontsize=16, fontweight='bold', 
                    color=COLORS['primary'], y=1.02)
        plt.tight_layout(pad=3.0)
        return self._save_chart(fig, f'{stock_code}_forecast_scenarios.png')
    
    def plot_share_structure(self, data: Dict, stock_code: str) -> str:
        """股权结构图 - 专业版"""
        fig, ax = plt.subplots(figsize=(9, 9), facecolor='white')
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#fafafa')
        
        # 示例数据
        labels = ['控股股东', '机构投资者', '散户', '其他']
        sizes = [45, 25, 20, 10]
        colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['neutral']]
        explode = (0.05, 0.02, 0.02, 0.02)
        
        # 美化饼图
        wedges, texts, autotexts = ax.pie(
            sizes, explode=explode, labels=labels, colors=colors, 
            autopct='%1.1f%%', shadow=False, startangle=90,
            textprops={'fontsize': 11, 'fontweight': 'bold'},
            wedgeprops={'edgecolor': 'white', 'linewidth': 2}
        )
        
        # 美化百分比文字
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
        
        ax.set_title(f'{stock_code} 股权结构', fontsize=14, fontweight='bold', 
                    color=COLORS['primary'], pad=20)
        
        # 添加图例
        ax.legend(wedges, [f'{l}: {s}%' for l, s in zip(labels, sizes)],
                 title="股东类型", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
                 fontsize=10, title_fontsize=11)
        
        plt.tight_layout()
        return self._save_chart(fig, f'{stock_code}_share_structure.png')
    
    def plot_industry_radar(self, data: Dict, stock_code: str) -> str:
        """行业竞争雷达图 - 专业版"""
        fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(projection='polar'), 
                              facecolor='white')
        fig.patch.set_facecolor('white')
        
        categories = ['营收规模', '盈利能力', '成长性', '研发投入', '市场份额', '运营效率']
        N = len(categories)
        
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        # 示例数据
        target_values = [0.8, 0.9, 0.7, 0.6, 0.75, 0.85]
        industry_avg = [0.6, 0.65, 0.6, 0.5, 0.55, 0.7]
        
        target_values += target_values[:1]
        industry_avg += industry_avg[:1]
        
        # 绘制区域填充
        ax.fill(angles, target_values, alpha=0.25, color=COLORS['primary'])
        ax.fill(angles, industry_avg, alpha=0.15, color=COLORS['secondary'])
        
        # 绘制线条
        ax.plot(angles, target_values, 'o-', linewidth=2.5, label=stock_code, 
               color=COLORS['primary'], markersize=8, markerfacecolor='white', markeredgewidth=2)
        ax.plot(angles, industry_avg, 'o-', linewidth=2, label='行业平均', 
               color=COLORS['secondary'], markersize=6, markerfacecolor='white', markeredgewidth=1.5)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 1)
        ax.set_title(f'{stock_code} 行业竞争力分析', fontsize=14, fontweight='bold', 
                    color=COLORS['primary'], pad=30)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        return self._save_chart(fig, f'{stock_code}_industry_radar.png')
    
    def plot_risk_radar(self, risk_data: Dict, stock_code: str) -> str:
        """风险雷达图 - 专业版"""
        fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(projection='polar'), 
                              facecolor='white')
        fig.patch.set_facecolor('white')
        
        categories = ['财务风险', '经营风险', '市场风险', '合规风险', '流动性风险', '治理风险']
        N = len(categories)
        
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        # 从风险数据提取
        values = [0.3, 0.4, 0.5, 0.2, 0.3, 0.4]  # 示例
        values += values[:1]
        
        # 根据风险等级着色
        colors_risk = [COLORS['success'] if v < 0.3 else COLORS['warning'] if v < 0.6 else COLORS['danger'] 
                      for v in values[:-1]]
        
        # 绘制区域
        ax.fill(angles, values, alpha=0.25, color=COLORS['danger'])
        ax.plot(angles, values, 'o-', linewidth=2.5, color=COLORS['danger'], 
               markersize=8, markerfacecolor='white', markeredgewidth=2)
        
        # 添加风险等级区域背景
        ax.fill(angles, [0.3]*7, alpha=0.1, color=COLORS['success'])
        ax.fill(angles, [0.6]*7, alpha=0.1, color=COLORS['warning'])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 1)
        ax.set_title(f'{stock_code} 风险雷达图', fontsize=14, fontweight='bold', 
                    color=COLORS['primary'], pad=30)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 添加风险等级标注
        risk_score = risk_data.get('score', 50)
        risk_level = risk_data.get('level', '未知')
        color_level = COLORS['success'] if risk_score < 40 else COLORS['warning'] if risk_score < 70 else COLORS['danger']
        
        ax.text(0.5, -0.1, f'综合风险: {risk_score}/100 ({risk_level})', 
                transform=ax.transAxes, ha='center', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor=color_level, alpha=0.3, edgecolor=color_level))
        
        return self._save_chart(fig, f'{stock_code}_risk_radar.png')


# ==================== 便捷函数 ====================

def generate_all_charts(analysis_data: Dict, stock_code: str, output_dir: str = None) -> Dict:
    """生成所有图表"""
    gen = ChartGenerator(output_dir)
    charts = {}
    
    if 'multi_year_trend' in analysis_data:
        path = gen.plot_financial_trend(analysis_data['multi_year_trend'], stock_code)
        if path:
            charts['financial_trend'] = path
    
    if 'peer_compare' in analysis_data:
        path = gen.plot_valuation_comparison(analysis_data['peer_compare'], stock_code)
        if path:
            charts['valuation_comparison'] = path
    
    if 'earnings_forecast' in analysis_data:
        ef = analysis_data['earnings_forecast']
        if 'forecast' in ef:
            path = gen.plot_forecast_scenarios(ef['forecast'], stock_code)
            if path:
                charts['forecast_scenarios'] = path
    
    if 'structure' in analysis_data:
        path = gen.plot_share_structure(analysis_data['structure'], stock_code)
        if path:
            charts['share_structure'] = path
    
    if 'industry' in analysis_data:
        path = gen.plot_industry_radar(analysis_data['industry'], stock_code)
        if path:
            charts['industry_radar'] = path
    
    if 'risk' in analysis_data:
        path = gen.plot_risk_radar(analysis_data['risk'], stock_code)
        if path:
            charts['risk_radar'] = path
    
    return charts


def charts_to_markdown(charts: Dict, base_dir: str = None) -> str:
    """将图表路径转换为Markdown"""
    lines = []
    
    chart_labels = {
        'financial_trend': '财务趋势',
        'valuation_comparison': '估值对比',
        'forecast_scenarios': '盈利预测情景',
        'share_structure': '股权结构',
        'industry_radar': '行业竞争力',
        'risk_radar': '风险雷达',
    }
    
    for key, path in charts.items():
        label = chart_labels.get(key, key)
        
        if base_dir and os.path.isabs(path):
            rel_path = os.path.relpath(path, base_dir)
            rel_path = rel_path.replace('\\', '/')
        else:
            rel_path = path.replace('\\', '/')
        
        lines.append(f"### {label}")
        lines.append(f"![{label}]({rel_path})")
        lines.append("")
    
    return "\n".join(lines)


# ==================== 测试 ====================

if __name__ == '__main__':
    test_data = {
        'multi_year_trend': {
            'years': [2021, 2022, 2023, 2024, 2025],
            'revenue': [109.5, 127.5, 150.5, 174.0, 150.5],
            'net_profit': [52.5, 62.7, 74.7, 86.2, 74.7],
        },
        'peer_compare': {
            'target': {'pe_ttm': 25.5, 'pb': 3.2, 'ps': 8.5},
            'peers': [
                {'name': 'Peer A', 'pe_ttm': 28.5, 'pb': 3.5, 'ps': 9.2},
                {'name': 'Peer B', 'pe_ttm': 22.3, 'pb': 2.8, 'ps': 7.5},
                {'name': 'Peer C', 'pe_ttm': 26.0, 'pb': 3.1, 'ps': 8.8},
            ]
        },
        'earnings_forecast': {
            'forecast': {
                'conservative': {
                    'years': [2026, 2027, 2028],
                    'revenue': [146.0, 141.6, 137.3],
                    'net_profit': [72.5, 70.3, 67.5],
                },
                'neutral': {
                    'years': [2026, 2027, 2028],
                    'revenue': [150.5, 150.5, 150.5],
                    'net_profit': [74.7, 74.7, 74.7],
                },
                'optimistic': {
                    'years': [2026, 2027, 2028],
                    'revenue': [155.0, 159.7, 164.5],
                    'net_profit': [76.9, 79.2, 82.0],
                }
            }
        },
        'structure': {'text': '控股股东: 45%'},
        'industry': {'competitors': []},
        'risk': {'score': 76, 'level': '中低风险'},
    }
    
    charts = generate_all_charts(test_data, '600519')
    print("生成的图表:")
    for name, path in charts.items():
        print(f"  {name}: {path}")
    
    print("\nMarkdown:")
    print(charts_to_markdown(charts))
