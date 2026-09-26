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
            const ca = document.getElementById('content-area');
            
            // Check all children of ca and their styles/rects
            const caChildren = Array.from(ca.children).map(c => {
                const s = window.getComputedStyle(c);
                const r = c.getBoundingClientRect();
                return {
                    id: c.id,
                    tagName: c.tagName,
                    display: s.display,
                    height: r.height,
                    top: r.top,
                    bottom: r.bottom
                };
            });
            
            return {
                paneParentId: parent.id,
                paneParentTag: parent.tagName,
                caChildren: caChildren
            };
        }""")
        print("Layout Info:", info)
        await browser.close()

asyncio.run(run())
