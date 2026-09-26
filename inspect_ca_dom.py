import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(1000)
        
        # Check what elements have clientHeight > 0 inside main or content-area
        res = await page.evaluate("""() => {
            const ca = document.getElementById('content-area');
            const items = [];
            for (let c of ca.children) {
                const s = window.getComputedStyle(c);
                const r = c.getBoundingClientRect();
                items.push({
                    id: c.id,
                    tagName: c.tagName,
                    display: s.display,
                    height: r.height,
                    top: r.top,
                    bottom: r.bottom
                });
            }
            return {
                caRect: ca.getBoundingClientRect(),
                items: items
            };
        }""")
        print("DOM Inspection inside #content-area:\n", res)
        await browser.close()

asyncio.run(run())
