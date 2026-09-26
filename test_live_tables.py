import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print("[BROWSER CONSOLE]", msg.type, msg.text))
        page.on("pageerror", lambda err: print("[BROWSER PAGE ERROR]", err))
        
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Test clicking pane-groups
        print("--- Testing pane-groups ---")
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(1500)
        content_g = await page.inner_html('#loha-groups-table-body')
        print("Groups table rows:\n", content_g)

        # Test clicking pane-tokens
        print("\n--- Testing pane-tokens ---")
        await page.click('.nav-btn[data-pane="pane-tokens"]')
        await page.wait_for_timeout(1500)
        content_t = await page.inner_html('#tokens-table-body')
        print("Tokens table rows snippet:\n", content_t[:800])

        await browser.close()

asyncio.run(run())
