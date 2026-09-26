import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR]: {err}"))
        
        await page.goto("http://127.0.0.1:5080/", wait_until="networkidle")
        
        # Call loadLoHaGroups directly in page context and see what happens!
        print("\n--- Calling loadLoHaGroups directly ---")
        res = await page.evaluate("""async () => {
            try {
                if (typeof loadLoHaGroups === 'function') {
                    await loadLoHaGroups();
                    return { success: true, html: document.getElementById('loha-groups-table-body')?.innerHTML };
                } else {
                    return { success: false, error: 'loadLoHaGroups is not a function' };
                }
            } catch(e) {
                return { success: false, error: e.toString() };
            }
        }""")
        print("Result:", res)

        print("\n--- Calling loadTokensOnly directly ---")
        res_t = await page.evaluate("""async () => {
            try {
                if (typeof loadTokensOnly === 'function') {
                    await loadTokensOnly();
                    return { success: true, html: document.getElementById('tokens-table-body')?.innerHTML?.substring(0, 300) };
                } else {
                    return { success: false, error: 'loadTokensOnly is not a function' };
                }
            } catch(e) {
                return { success: false, error: e.toString() };
            }
        }""")
        print("Result tokens:", res_t)

        await browser.close()

asyncio.run(run())
