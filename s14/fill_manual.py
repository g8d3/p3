from pypdf import PdfReader, PdfWriter

def fill_manual(template_path, output_path):
    reader = PdfReader(template_path)

    # Get fields
    fields = reader.get_fields()
    field_names = list(fields.keys())

    print(f"Found {len(field_names)} fields. Auto-filling all with their field names for visual verification...")
    data_dict = {name: name for name in field_names}

    # Create writer with form
    writer = PdfWriter(clone_from=reader)

    # Fill fields
    writer.update_page_form_field_values(writer.pages[0], data_dict)

    with open(output_path, 'wb') as f:
        writer.write(f)
    print(f"Saved filled PDF to {output_path}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python fill_manual.py <template_path> <output_path>")
        sys.exit(1)
    template = sys.argv[1]
    output = sys.argv[2]
    fill_manual(template, output)