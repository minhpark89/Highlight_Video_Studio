import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(1000)
        
        # Check layout again
        info = await page.evaluate("""() => {
            const el = document.getElementById('pane-groups');
            const rect = el ? el.getBoundingClientRect() : null;
            return {
                paneTop: rect ? rect.top : null,
                paneHeight: rect ? rect.height : null
            };
        }""")
        print("Updated pane-groups layout:", info)
        await browser.close()

asyncio.run(run())
