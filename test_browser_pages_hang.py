import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Listen for console errors
        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
        
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Switch to pane-pages
        await page.click('.nav-btn[data-pane="pane-pages"]')
        await page.wait_for_timeout(2000)
        
        # Check text in #pages-cards-container
        container_text = await page.inner_text('#pages-cards-container')
        print("=== pages-cards-container text ===")
        print(container_text[:500])
        
        # Check badge count
        badge = await page.inner_text('#page-filtered-count-badge')
        print("=== page-filtered-count-badge ===", badge)
        
        await browser.close()

asyncio.run(run())
