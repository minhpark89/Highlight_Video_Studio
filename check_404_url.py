import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        failed_requests = []
        page.on("requestfailed", lambda req: failed_requests.append(f"{req.url}: {req.failure}"))
        page.on("response", lambda res: print(f"[{res.status}] {res.url}") if res.status >= 400 else None)
        
        await page.goto("http://127.0.0.1:5080/")
        await asyncio.sleep(1)
        
        print("Failed requests:", failed_requests)
        await browser.close()

asyncio.run(run())
