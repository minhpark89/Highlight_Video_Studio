import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Click pane-groups
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(1000)
        
        # Check table
        table_g = await page.inner_text('#loha-groups-table-body')
        print("=== Groups table content ===")
        print(table_g.strip())

        # Click pane-tokens
        await page.click('.nav-btn[data-pane="pane-tokens"]')
        await page.wait_for_timeout(1000)
        
        table_t = await page.inner_text('#tokens-table-body')
        print("=== Tokens table content (first 300 chars) ===")
        print(table_t.strip()[:300])

        await browser.close()

asyncio.run(run())
