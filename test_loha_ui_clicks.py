import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to http://127.0.0.1:5080/ ...")
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Test clicking new tabs: pane-groups, pane-pages, pane-tokens, pane-posts
        tabs_to_test = [
            ("Nhóm Trang", "pane-groups"),
            ("100 Fanpage", "pane-pages"),
            ("Quản lý Token", "pane-tokens"),
            ("Quản lý Bài Đăng", "pane-posts"),
            ("Website bài viết", "pane-website")
        ]
        
        for name, pane_id in tabs_to_test:
            btn = await page.query_selector(f'.nav-btn[data-pane="{pane_id}"]')
            if btn:
                await btn.click()
                await page.wait_for_timeout(500)
                pane = await page.query_selector(f'#{pane_id}')
                is_visible = await pane.is_visible()
                print(f"Tab [{name}] -> #{pane_id}: visible = {is_visible}")
            else:
                print(f"Tab button for #{pane_id} NOT found!")
                
        await browser.close()

asyncio.run(run())
