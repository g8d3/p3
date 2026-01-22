import json
import os
import urllib.request
import glob
from pdfrw import PdfReader, PdfWriter, PdfName, PdfObject, PdfString

# --- SISTEMA CRUD SIMPLE (Simulado con archivos JSON) ---

class LLCTaxSystem:
    def __init__(self):
        self.profiles_file = 'profiles.json'
        self.tx_file = 'transactions.json'

    def create_profile(self, profile_id, name, ein, address, foreign_id, country):
        data = self._load(self.profiles_file)
        data[profile_id] = {
            "name": name, "ein": ein, "address": address,
            "foreign_id": foreign_id, "country": country
        }
        self._save(self.profiles_file, data)

    def add_transaction(self, profile_id, year, type_tx, amount):
        # type_tx: 'capital_in', 'distribution', 'loan', etc.
        data = self._load(self.tx_file)
        if profile_id not in data: data[profile_id] = {}
        if str(year) not in data[profile_id]: data[profile_id][str(year)] = []
        
        data[profile_id][str(year)].append({"type": type_tx, "amount": amount})
        self._save(self.tx_file, data)

    def _save(self, filename, data):
        with open(filename, 'w') as f: json.dump(data, f)

    def _load(self, filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except FileNotFoundError: return {}

    # --- MOTOR DE LLENADO DE PDF ---

    def list_pdf_fields(self, template_path):
        if not os.path.exists(template_path):
            print(f"Template {template_path} not found. Downloading from IRS...")
            try:
                if 'f5472' in template_path:
                    url = 'https://www.irs.gov/pub/irs-pdf/f5472.pdf'
                elif 'f1120f' in template_path:
                    url = 'https://www.irs.gov/pub/irs-pdf/f1120f.pdf'
                else:
                    raise ValueError(f"Unknown template: {template_path}")
                urllib.request.urlretrieve(url, template_path)
                print("Template downloaded successfully.")
            except Exception as e:
                raise FileNotFoundError(f"Failed to download template: {e}")
        template = PdfReader(template_path)
        fields = []
        for page in template.pages:
            annotations = page.get('/Annots')
            if annotations:
                for annotation in annotations:
                    if annotation.get('/Subtype') == PdfName.Widget:
                        field_name = annotation.get('/T')
                        if field_name:
                            raw_key = field_name[1:-1] if field_name.startswith('(') else field_name
                            try:
                                key = raw_key.encode('latin1').decode('utf-16').lstrip('\ufeff')
                            except Exception as e:
                                fields.append(raw_key)
                            else:
                                fields.append(key)
        return fields

    def fill_pdf(self, template_path, output_path, data_dict):
        if not os.path.exists(template_path):
            print(f"Template {template_path} not found. Downloading from IRS...")
            try:
                if 'f5472' in template_path:
                    url = 'https://www.irs.gov/pub/irs-pdf/f5472.pdf'
                elif 'f1120f' in template_path:
                    url = 'https://www.irs.gov/pub/irs-pdf/f1120f.pdf'
                else:
                    raise ValueError(f"Unknown template: {template_path}")
                urllib.request.urlretrieve(url, template_path)
                print("Template downloaded successfully.")
            except Exception as e:
                raise FileNotFoundError(f"Failed to download template: {e}")
        template = PdfReader(template_path)
        if '/AcroForm' in template.Root:
            template.Root.AcroForm[PdfName('/NeedAppearances')] = PdfObject('true')
        for page in template.pages:
            annotations = page.get('/Annots')
            if annotations:
                for annotation in annotations:
                    if annotation.get('/Subtype') == PdfName.Widget:
                        field_name = annotation.get('/T')
                        if field_name:
                            raw_key = field_name[1:-1] if field_name.startswith('(') else field_name
                            try:
                                key = raw_key.encode('latin1').decode('utf-16').lstrip('\ufeff')
                            except Exception as e:
                                key = raw_key
                            if key in data_dict:
                                annotation[PdfName('/V')] = PdfString(data_dict[key])
                                annotation[PdfName('/AP')] = None  # Force regeneration of appearance
        PdfWriter().write(output_path, template)
        # Flatten the PDF to make filled fields visible
        try:
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(output_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.add_metadata(reader.metadata)
            with open(output_path, 'wb') as f:
                writer.write(f)
        except ImportError:
            pass  # Flattening not available

    def prepare_tax_forms(self, profile_id, year):
        profile = self._load(self.profiles_file).get(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        txs = self._load(self.tx_file).get(profile_id, {}).get(str(year), [])
        
        # Sumar transacciones por tipo
        total_in = sum(t['amount'] for t in txs if t['type'] == 'capital_in')
        total_out = sum(t['amount'] for t in txs if t['type'] == 'distribution')

        # Mapeo de campos para f5472
        f5472_data = {
            "f1_1[0]": profile['name'],
            "f1_2[0]": profile['ein'],
            "f1_3[0]": profile['address'],
            "f1_4[0]": profile['foreign_id'],
            "f4_1[0]": str(total_in),
            "f4_2[0]": str(total_out),
        }

        # Mapeo de campos para f1120f (pro forma)
        f1120f_data = {
            "f1_1[0]": profile['name'],
            "f1_2[0]": profile['ein'],
            "f1_3[0]": profile['address'],
            # Add more fields as needed
        }
        print("1120F data:", f1120f_data)
        
        print(f"Generando borradores para {profile['name']} - Año {year}...")
        try:
            self.fill_pdf('f5472_template.pdf', f'5472_{profile_id}_{year}.pdf', f5472_data)
            self.fill_pdf('f1120f_template.pdf', f'1120F_{profile_id}_{year}.pdf', f1120f_data)
            print("¡Completado! Revise los archivos generados (5472 y 1120-F) antes de enviar al EA.")
        except Exception as e:
            print(f"Error al generar PDF: {e}. Asegúrese de que los templates estén disponibles.")

    def verify_pdf(self, pdf_path):
        pdf = PdfReader(pdf_path)
        filled = {}
        for page in pdf.pages:
            annotations = page.get('/Annots')
            if annotations:
                for annotation in annotations:
                    if annotation.get('/Subtype') == PdfName.Widget:
                        field_name = annotation.get('/T')
                        if field_name:
                            raw_key = field_name[1:-1] if field_name.startswith('(') else field_name
                            try:
                                key = raw_key.encode('latin1').decode('utf-16').lstrip('\ufeff')
                            except Exception as e:
                                key = raw_key
                            value = annotation.get(PdfName('/V'))
                            if value:
                                if hasattr(value, 'to_unicode'):
                                    filled[key] = value.to_unicode()
                                else:
                                    filled[key] = str(value)
        print("Filled fields:", filled)
        return filled

    def list_profiles_dict(self):
        return self._load(self.profiles_file)

    def list_profiles(self):
        profiles = self.list_profiles_dict()
        if not profiles:
            print("No profiles found.")
        else:
            for pid, p in profiles.items():
                print(f"{pid}: {p}")

    def list_transactions_dict(self, profile_id):
        return self._load(self.tx_file).get(profile_id, {})

    def list_transactions(self, profile_id):
        txs = self.list_transactions_dict(profile_id)
        if not txs:
            print(f"No transactions for {profile_id}.")
        else:
            for year, trans in txs.items():
                print(f"Year {year}: {trans}")

def main_menu():
    sys = LLCTaxSystem()
    while True:
        print("\nMenu:")
        print("1. Create Profile")
        print("2. Add Transaction")
        print("3. List Profiles")
        print("4. List Transactions for Profile")
        print("5. Generate PDF")
        print("6. Verify PDF")
        print("7. List PDF Fields")
        print("8. Load Test Data")
        print("9. Exit")
        choice = input("Choose option: ")
        if choice == '1':
            profile_id = input("Profile ID: ")
            name = input("Name: ")
            ein = input("EIN: ")
            address = input("Address: ")
            foreign_id = input("Foreign ID: ")
            country = input("Country: ")
            sys.create_profile(profile_id, name, ein, address, foreign_id, country)
        elif choice == '2':
            profiles = sys.list_profiles_dict()
            if not profiles:
                print("No profiles available. Create one first.")
                continue
            print("Available profiles:")
            for i, (pid, p) in enumerate(profiles.items(), 1):
                print(f"{i}. {pid}: {p['name']}")
            try:
                idx = int(input("Choose profile number: ")) - 1
                pid = list(profiles.keys())[idx]
            except (ValueError, IndexError):
                print("Invalid choice.")
                continue
            year = int(input("Year: "))
            type_tx = input("Type (capital_in/distribution): ")
            amount = float(input("Amount: "))
            sys.add_transaction(pid, year, type_tx, amount)
        elif choice == '3':
            sys.list_profiles()
        elif choice == '4':
            profiles = sys.list_profiles_dict()
            if not profiles:
                print("No profiles available.")
                continue
            print("Available profiles:")
            for i, (pid, p) in enumerate(profiles.items(), 1):
                print(f"{i}. {pid}: {p['name']}")
            try:
                idx = int(input("Choose profile number: ")) - 1
                pid = list(profiles.keys())[idx]
            except (ValueError, IndexError):
                print("Invalid choice.")
                continue
            sys.list_transactions(pid)
        elif choice == '5':
            profiles = sys.list_profiles_dict()
            if not profiles:
                print("No profiles available. Create one first.")
                continue
            print("Available profiles:")
            for i, (pid, p) in enumerate(profiles.items(), 1):
                print(f"{i}. {pid}: {p['name']}")
            try:
                idx = int(input("Choose profile number: ")) - 1
                pid = list(profiles.keys())[idx]
            except (ValueError, IndexError):
                print("Invalid choice.")
                continue
            txs_dict = sys.list_transactions_dict(pid)
            years = list(txs_dict.keys())
            if years:
                print(f"Available years for {pid}: {', '.join(years)}")
            year = int(input("Year: "))
            sys.prepare_tax_forms(pid, year)
        elif choice == '6':
            pdfs = glob.glob('*.pdf')
            if not pdfs:
                print("No PDF files found.")
                continue
            print("Available PDFs:")
            for i, pdf in enumerate(pdfs, 1):
                print(f"{i}. {pdf}")
            try:
                idx = int(input("Choose PDF number: ")) - 1
                pdf_path = pdfs[idx]
            except (ValueError, IndexError):
                print("Invalid choice.")
                continue
            sys.verify_pdf(pdf_path)
        elif choice == '7':
            fields = sys.list_pdf_fields('f5472_template.pdf')
            print("PDF Fields:", fields[:10])  # Show first 10
        elif choice == '8':
            # Load test data
            sys.create_profile("mi_llc_1", "Giga Ventures LLC", "12-3456789", "123 Street, DE", "ID12345", "Colombia")
            sys.add_transaction("mi_llc_1", 2025, "capital_in", 5000)
            sys.add_transaction("mi_llc_1", 2025, "distribution", 200)
            print("Test data loaded.")
        elif choice == '9':
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()
