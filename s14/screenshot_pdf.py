import asyncio
import sys
import argparse
import os

async def screenshot_pdf(pdf_path, port):
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            page = await browser.new_page()
            await page.goto(f'file://{os.path.abspath(pdf_path)}')
            await asyncio.sleep(2)  # Wait for PDF to load
            await page.screenshot(path=f'{pdf_path}.png')
            await browser.close()
            print(f"Screenshot saved to {pdf_path}.png")
    except Exception as e:
        print(f"Could not screenshot {pdf_path}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Screenshot a PDF using CDP")
    parser.add_argument('-p', '--port', type=int, default=9222, help='CDP port (default: 9222)')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    args = parser.parse_args()
    asyncio.run(screenshot_pdf(args.pdf_path, args.port))