import unittest
import os
import json
import asyncio
from main import LLCTaxSystem

async def screenshot_pdf(pdf_path):
    try:
        from pyppeteer import connect
        browser = await connect(browserWSEndpoint='ws://localhost:9222')
        page = await browser.newPage()
        await page.goto(f'file://{os.path.abspath(pdf_path)}')
        await page.waitFor(2000)  # Wait for PDF to load
        await page.screenshot(path=f'{pdf_path}.png')
        await browser.close()
        print(f"Screenshot saved to {pdf_path}.png")
    except Exception as e:
        print(f"Could not screenshot: {e}")

class TestLLCTaxSystem(unittest.TestCase):
    def setUp(self):
        self.sys = LLCTaxSystem()
        # Clean up JSON files, but keep templates
        for f in ['profiles.json', 'transactions.json']:
            if os.path.exists(f):
                os.remove(f)

    def tearDown(self):
        # Clean up after tests: remove JSON files, but keep templates and PDFs for inspection
        for f in ['profiles.json', 'transactions.json']:
            if os.path.exists(f):
                os.remove(f)
        # Optionally, keep only the latest 3 PDFs (by modification time)
        import glob
        pdfs = [p for p in glob.glob('*.pdf') if p not in ['f5472_template.pdf', 'f1120f_template.pdf']]
        if len(pdfs) > 3:
            pdfs.sort(key=os.path.getmtime, reverse=True)
            for pdf in pdfs[3:]:
                os.remove(pdf)

    def test_create_profile(self):
        self.sys.create_profile("test_id", "Test LLC", "12-3456789", "123 Test St", "ID123", "USA")
        profiles = self.sys.list_profiles_dict()
        self.assertIn("test_id", profiles)
        self.assertEqual(profiles["test_id"]["name"], "Test LLC")

    def test_add_transaction(self):
        self.sys.create_profile("test_id", "Test LLC", "12-3456789", "123 Test St", "ID123", "USA")
        self.sys.add_transaction("test_id", 2025, "capital_in", 1000)
        txs = self.sys.list_transactions_dict("test_id")
        self.assertIn("2025", txs)
        self.assertEqual(len(txs["2025"]), 1)
        self.assertEqual(txs["2025"][0]["type"], "capital_in")
        self.assertEqual(txs["2025"][0]["amount"], 1000)

    def test_prepare_tax_forms_creates_pdfs(self):
        self.sys.create_profile("test_id", "Test LLC", "12-3456789", "123 Test St", "ID123", "USA")
        self.sys.add_transaction("test_id", 2025, "capital_in", 1000)
        self.sys.prepare_tax_forms("test_id", 2025)
        self.assertTrue(os.path.exists("5472_test_id_2025.pdf"))
        self.assertTrue(os.path.exists("1120F_test_id_2025.pdf"))

    def test_verify_pdf_has_fields(self):
        # First create and generate PDF
        self.test_prepare_tax_forms_creates_pdfs()
        filled = self.sys.verify_pdf("5472_test_id_2025.pdf")
        self.assertIn("f1_1[0]", filled)
        # Note: PDF fields may truncate values; check that data is set
        self.assertTrue(filled["f1_1[0]"])  # At least not empty

    def test_fill_manual_creates_pdf(self):
        from fill_manual import fill_manual
        fill_manual('f5472_template.pdf', 'manual_test.pdf')
        self.assertTrue(os.path.exists('manual_test.pdf'))
        # Clean up
        if os.path.exists('manual_test.pdf'):
            os.remove('manual_test.pdf')

if __name__ == '__main__':
    unittest.main()