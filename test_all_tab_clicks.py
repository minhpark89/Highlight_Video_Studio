import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: print(f"[{m.type}] {m.text}"))
        
        await page.goto("http://127.0.0.1:5080/")
        await asyncio.sleep(1)
        
        print("--- CLICKING TABS ---")
        tabs = ["pane-studio", "pane-jobs", "pane-gallery", "pane-tokens", "pane-pages", "pane-website"]
        for t in tabs:
            btn = await page.query_selector(f'button[data-pane="{t}"]')
            if btn:
                await btn.click()
                await asyncio.sleep(0.3)
                is_active = await page.evaluate(f"() => document.getElementById('{t}') && document.getElementById('{t}').classList.contains('active')")
                display = await page.evaluate(f"() => document.getElementById('{t}') ? window.getComputedStyle(document.getElementById('{t}')).display : 'none'")
                print(f"Tab {t}: active={is_active}, display={display}")
            else:
                print(f"Button {t} not found!")
                
        print("Page errors:", errors)
        await browser.close()

asyncio.run(run())
