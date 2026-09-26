import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR]: {err}"))
        
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Click pane-groups
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(2000)
        
        html_g = await page.inner_html('#loha-groups-table-body')
        print("[Groups Table Body]:\n", html_g)

        # Click pane-tokens
        await page.click('.nav-btn[data-pane="pane-tokens"]')
        await page.wait_for_timeout(2000)
        
        html_t = await page.inner_html('#tokens-table-body')
        print("[Tokens Table Body]:\n", html_t[:600])

        await browser.close()

asyncio.run(run())
