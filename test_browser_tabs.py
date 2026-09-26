import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        
        errors = []
        logs = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
        
        await page.goto("http://127.0.0.1:5080/")
        await asyncio.sleep(1)
        
        print("=== INITIAL LOAD ===")
        print("Page title:", await page.title())
        print("Errors on load:", errors)
        for l in logs[-10:]:
            print(" ", l)
            
        # Thử click vào nút "Quản lý Page & Token"
        print("\n--- Clicking 'Quản lý Page & Token' (pane-pages) ---")
        btn_pages = await page.query_selector('button[data-pane="pane-pages"]')
        if btn_pages:
            await btn_pages.click()
            await asyncio.sleep(1)
            
            # Kiểm tra xem pane nào đang active và display là gì
            panes_state = await page.evaluate('''() => {
                const results = {};
                document.querySelectorAll('.pane').forEach(p => {
                    results[p.id] = {
                        className: p.className,
                        display: window.getComputedStyle(p).display,
                        offsetHeight: p.offsetHeight,
                        innerHTML_len: p.innerHTML.length
                    };
                });
                return results;
            }''')
            print("Panes state after clicking pane-pages:")
            for pid, st in panes_state.items():
                if "active" in st["className"] or st["display"] != "none":
                    print(f"  * {pid}: {st}")
        else:
            print("button[data-pane='pane-pages'] NOT FOUND!")
            
        print("Errors after click:", errors)
        
        # Chụp ảnh màn hình kiểm chứng
        await page.screenshot(path=r"D:\Highlight_Video_Studio\test_tab_click_result.png")
        print("Screenshot saved to D:\\Highlight_Video_Studio\\test_tab_click_result.png")
        await browser.close()

asyncio.run(run())
