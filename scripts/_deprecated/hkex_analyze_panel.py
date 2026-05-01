"""港交所公告搜索 - 分析搜索面板结构"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 1. 访问搜索页
    page.goto('https://www1.hkexnews.hk/search/titlesearch.xhtml', timeout=30000)
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    # 接受Cookie
    try:
        page.locator('button:has-text("Accept")').first.click(timeout=3000)
        time.sleep(1)
    except:
        pass
    
    # 2. 查找所有frame
    frames = page.frames
    print(f'Frame数: {len(frames)}')
    for i, frame in enumerate(frames):
        print(f'  Frame {i}: {frame.url[:80]}')
    
    # 3. 在主页面查找搜索面板
    # 搜索面板通过AJAX加载到 #searchPanel
    panel = page.locator('#searchPanel')
    print(f'\n#searchPanel: visible={panel.is_visible()}, html_len={len(panel.inner_html()[:100]) if panel.is_visible() else 0}')
    
    # 4. 检查所有输入框
    inputs = page.locator('input').all()
    print(f'\n所有input: {len(inputs)}')
    for inp in inputs:
        try:
            id_val = inp.get_attribute('id') or ''
            name_val = inp.get_attribute('name') or ''
            type_val = inp.get_attribute('type') or ''
            visible = inp.is_visible()
            print(f'  id={id_val[:30]}, name={name_val[:30]}, type={type_val}, visible={visible}')
        except:
            pass
    
    # 5. 检查自动补全相关元素
    autocomplete = page.locator('[class*="autocomplete"], [class*="Autocomplete"], .ui-autocomplete').all()
    print(f'\nAutocomplete元素: {len(autocomplete)}')
    for ac in autocomplete:
        try:
            print(f'  class={ac.get_attribute("class")[:60]}, visible={ac.is_visible()}')
        except:
            pass
    
    # 6. 尝试在搜索面板输入框中输入
    # 搜索面板可能是通过另一个HTML加载的
    # 检查面板HTML
    panel_html = page.evaluate('() => document.getElementById("searchPanel")?.innerHTML?.substring(0, 2000) || "not found"')
    print(f'\n搜索面板HTML（前2000字符）:')
    print(panel_html[:2000])
    
    # 7. 检查是否有iframe包含搜索面板
    iframes = page.locator('iframe').all()
    print(f'\niframe数: {len(iframes)}')
    for iframe in iframes:
        try:
            src = iframe.get_attribute('src') or ''
            print(f'  src={src[:80]}')
        except:
            pass
    
    browser.close()
