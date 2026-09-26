import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR]: {err}"))
        
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Test clicking pane-groups
        print("\n--- Click Tab Nhóm Trang ---")
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(1000)
        
        # Test clicking pane-tokens
        print("\n--- Click Tab Quản lý Token ---")
        await page.click('.nav-btn[data-pane="pane-tokens"]')
        await page.wait_for_timeout(1000)
        
        # Test clicking pane-pages
        print("\n--- Click Tab Quản lý Page ---")
        await page.click('.nav-btn[data-pane="pane-pages"]')
        await page.wait_for_timeout(1000)

        # Check groups table innerHTML
        html_g = await page.inner_html('#loha-groups-table-body')
        print("\n[Groups Table Body]:\n", html_g)

        # Check tokens table innerHTML
        html_t = await page.inner_html('#tokens-table-body')
        print("\n[Tokens Table Body Snippet]:\n", html_t[:500])

        await browser.close()

asyncio.run(run())
