# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
sys.stdout.reconfigure(encoding='utf-8')

from scripts.announcements import fetch_announcements
from scripts.financials import fetch_financials
from scripts.report import generate_report
from scripts.multi_year_trend import fetch_multi_year_trend
from scripts.valuation import fetch_valuation
from scripts.share_history import fetch_share_history
from scripts.institutional import fetch_institutional
from datetime import datetime

print('=== 600519 Guizhou Maotai ===')
findings = {}

# Test core dimensions only
try:
    r = fetch_announcements('600519', 'a')
    if r: 
        findings['announcements'] = r
        print('announcements: OK')
except Exception as e:
    print(f'announcements: {e}')

try:
    r = fetch_financials('600519', 'a')
    if r: 
        findings['financial'] = r
        print('financial: OK')
except Exception as e:
    print(f'financial: {e}')

try:
    r = fetch_multi_year_trend('600519', 'a')
    if r: 
        findings['multi_year_trend'] = r
        print('multi_year_trend: OK')
except Exception as e:
    print(f'multi_year_trend: {e}')

try:
    r = fetch_valuation('600519', 'a')
    if r: 
        findings['valuation'] = r
        print('valuation: OK')
except Exception as e:
    print(f'valuation: {e}')

try:
    r = fetch_share_history('600519', 'a')
    if r: 
        findings['share_history'] = r
        print('share_history: OK')
except Exception as e:
    print(f'share_history: {e}')

try:
    r = fetch_institutional('600519', 'a')
    if r: 
        findings['institutional'] = r
        print('institutional: OK')
except Exception as e:
    print(f'institutional: {e}')

print(f'\nDimensions executed: {len(findings)}')

# Generate report
result = {
    'stock': '600519',
    'market': 'a',
    'dims': list(findings.keys()),
    'findings': findings,
    'date': datetime.now().isoformat()
}

try:
    report = generate_report(result, None)
    # Count chapters
    chapters = [l for l in report.split('\n') if l.strip().startswith('## ')]
    print(f'\n=== REPORT CHAPTERS: {len(chapters)} ===')
    for i, c in enumerate(chapters[:25], 1):
        print(f'{i:2d}. {c[:70]}')
except Exception as e:
    print(f'Report generation failed: {e}')
    import traceback
    traceback.print_exc()