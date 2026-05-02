from PyPDF2 import PdfReader, PdfWriter

pdf_path = 'f1120f_template.pdf'

# Load and list fields
reader = PdfReader(pdf_path)
fields = reader.get_fields()
print("Fields in template:")
for name, field in list(fields.items())[:10]:  # First 10
    print(f"{name}: {field.get('/V', 'None')}")

# Fill some fields
writer = PdfWriter()
for page in reader.pages:
    writer.add_page(page)
writer.update_page_form_field_values(writer.pages[0], {
    'f1_1[0]': 'Test Name',
    'f1_2[0]': '12-3456789'
})
with open('test_filled.pdf', 'wb') as f:
    writer.write(f)

print("Saved test_filled.pdf")

# Verify
reader2 = PdfReader('test_filled.pdf')
fields2 = reader2.get_fields()
print("Filled fields:")
for name, field in list(fields2.items())[:10]:
    val = field.get('/V', 'None')
    if val != 'None' and val != '/Off':
        print(f"{name}: {val}")