import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Click Quản lý Token
        await page.click('.nav-btn[data-pane="pane-tokens"]')
        await page.wait_for_timeout(1000)
        
        # Check text in pane-tokens
        text = await page.inner_text('#pane-tokens')
        print("=== PANE-TOKENS TEXT ===")
        print(text[:800])
        
        # Check pills
        pills = await page.inner_html('#loha-token-group-pills')
        print("\n=== PILLS HTML ===\n", pills)

        await browser.close()

asyncio.run(run())
