import sys
sys.path.append('.')
from main import LLCTaxSystem

if len(sys.argv) != 2:
    print("Usage: python verify.py <pdf_path>")
    sys.exit(1)

pdf_path = sys.argv[1]

sys_inst = LLCTaxSystem()
filled = sys_inst.verify_pdf(pdf_path)
if filled:
    print("PDF has filled fields.")
else:
    print("PDF has no filled fields.")