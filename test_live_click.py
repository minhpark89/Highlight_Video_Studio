import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda msg: print(f"[{msg.type}] {msg.text}"))
        
        await page.goto("http://127.0.0.1:5080/")
        await asyncio.sleep(1)
        print("Page errors on load:", errors)
        
        # Thử click tab pane-studio (Cắt Highlight)
        print("Clicking button for pane-studio...")
        btn = await page.query_selector('button[data-pane="pane-studio"]')
        if btn:
            await btn.click()
            await asyncio.sleep(0.5)
            active_id = await page.evaluate("() => document.querySelector('.pane.active') ? document.querySelector('.pane.active').id : 'none'")
            print("Active pane after click:", active_id)
        else:
            print("Button not found!")
            
        print("Page errors after click:", errors)
        await browser.close()

asyncio.run(run())
