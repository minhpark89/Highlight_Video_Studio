import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Click pane-groups
        btn_g = await page.query_selector('.nav-btn[data-pane="pane-groups"]')
        if btn_g:
            await btn_g.click()
            await page.wait_for_timeout(800)
            text_g = await page.inner_text('#pane-groups')
            print("=== PANE-GROUPS TEXT ===")
            print(text_g[:600])
            
        # Click pane-tokens
        btn_t = await page.query_selector('.nav-btn[data-pane="pane-tokens"]')
        if btn_t:
            await btn_t.click()
            await page.wait_for_timeout(800)
            text_t = await page.inner_text('#pane-tokens')
            print("=== PANE-TOKENS TEXT ===")
            print(text_t[:600])

        await browser.close()

asyncio.run(run())
