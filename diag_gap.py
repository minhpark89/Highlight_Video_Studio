import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Click pane-groups
        await page.click('.nav-btn[data-pane="pane-groups"]')
        await page.wait_for_timeout(1000)
        
        # Get bounding box and computed style of #pane-groups and its parents
        info = await page.evaluate("""() => {
            const el = document.getElementById('pane-groups');
            const rect = el ? el.getBoundingClientRect() : null;
            const ca = document.getElementById('content-area');
            const caRect = ca ? ca.getBoundingClientRect() : null;
            
            // Check computed styles
            const computedEl = el ? window.getComputedStyle(el) : null;
            const computedCa = ca ? window.getComputedStyle(ca) : null;
            
            // Check children of content-area before pane-groups
            let prevElements = [];
            if (el && el.parentElement) {
                let child = el.parentElement.firstElementChild;
                while (child && child !== el) {
                    const r = child.getBoundingClientRect();
                    const s = window.getComputedStyle(child);
                    if (r.height > 0 || s.display !== 'none') {
                        prevElements.push({
                            id: child.id,
                            tagName: child.tagName,
                            className: child.className,
                            display: s.display,
                            visibility: s.visibility,
                            height: r.height,
                            top: r.top
                        });
                    }
                    child = child.nextElementSibling;
                }
            }

            return {
                paneRect: rect,
                caRect: caRect,
                prevElements: prevElements
            };
        }""")
        print("Layout Info:", info)
        await browser.close()

asyncio.run(run())
