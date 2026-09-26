import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(1000)
        
        # Check what elements have height > 0 between header and #pane-groups
        res = await page.evaluate("""() => {
            const el = document.getElementById('pane-groups');
            const rect = el.getBoundingClientRect();
            
            // Check all elements in document that take vertical space above el
            const all = Array.from(document.querySelectorAll('*'));
            const blockers = [];
            for (let e of all) {
                if (e === el || el.contains(e)) continue;
                const r = e.getBoundingClientRect();
                const style = window.getComputedStyle(e);
                if (r.height > 50 && r.bottom <= rect.top + 10 && style.display !== 'none' && style.visibility !== 'hidden') {
                    blockers.push({
                        id: e.id,
                        tag: e.tagName,
                        cls: e.className,
                        top: r.top,
                        bottom: r.bottom,
                        height: r.height
                    });
                }
            }
            return {
                paneTop: rect.top,
                blockers: blockers
            };
        }""")
        print("Diagnosis result:", res)
        await browser.close()

asyncio.run(run())
