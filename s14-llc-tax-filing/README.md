# LLC Tax System

A Python-based system for managing LLC profiles, transactions, and generating filled IRS tax forms (5472 and 1120-F).

## Features
- Create and manage LLC profiles and transactions.
- Automatically generate and fill IRS Form 5472 (Related Party Transactions) and Form 1120-F (Foreign Corporation Tax Return).
- Verify filled fields in generated PDFs.
- CLI interface for batch operations.
- Optional visual verification via browser screenshots.

## Installation
1. Activate the virtual environment: `source ~/code/pyenvs/3.10/bin/activate`
2. Install dependencies: `uv add pdfrw` (others are standard).

## Usage

### Interactive Menu
Run the main script: `python main.py`
- Choose options to create profiles, add transactions, generate PDFs, verify, etc.

### CLI Commands
- Load test data and generate PDFs: `python main.py --load-test --generate-pdf mi_llc_1 2025`
- Verify a PDF: `python verify.py 5472_mi_llc_1_2025.pdf`
- List profiles: `python main.py --list-profiles`
- List transactions: `python main.py --list-transactions mi_llc_1`
- Screenshot PDF: `python screenshot_pdf.py -p 9222 5472_mi_llc_1_2025.pdf`
- Manual fill PDF: `python fill_manual.py` (interactive field selection and filling)

### Verification
- Run tests: `python -m unittest test_main.py`
- Manual verification: Use `verify.py` on generated PDFs.
- Visual check: Open PDFs in a viewer or use `screenshot_pdf.py`.

## Scripts
- `main.py`: Core system with CLI and menu.
- `verify.py`: Verify filled fields in PDFs.
- `screenshot_pdf.py`: Take browser screenshots of PDFs.
- `test_main.py`: Unit tests.
- `test_fill.py`: Manual field filling test.

## Notes
- Templates are downloaded automatically if missing.
- Data verification confirms fields are filled; visual rendering may vary by viewer.
- For manual filling, see `test_fill.py` as an example.