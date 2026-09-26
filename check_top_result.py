import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(1000)
        
        info = await page.evaluate("""() => {
            const el = document.getElementById('pane-groups');
            const parent = el.parentElement;
            return {
                paneId: el.id,
                paneParentId: parent ? parent.id : null,
                paneParentTag: parent ? parent.tagName : null,
                paneRect: el.getBoundingClientRect()
            };
        }""")
        print("After moving to top of ca:", info)
        await browser.close()

asyncio.run(run())
