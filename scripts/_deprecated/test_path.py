# -*- coding: utf-8 -*-
import sys, os
# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

# Now import should work
try:
    from skills.listed_company_analysis.scripts.announcements import fetch_announcements
    print('import announcements: OK')
except Exception as e:
    print(f'import error: {e}')
    # Try alternative import
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
    try:
        import announcements as ann
        from announcements import fetch_announcements
        print('announcements import: fallback OK')
    except Exception as e2:
        print(f'fallback error: {e2}')