const { PDFDocument } = require('pdf-lib');
const fs = require('fs');
const https = require('https');

async function downloadPdf(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => resolve(Buffer.concat(chunks)));
    }).on('error', reject);
  });
}

async function fillManual() {
  try {
    // Download the template (Form 5472)
    const url = 'https://www.irs.gov/pub/irs-pdf/f5472.pdf';
    console.log('Downloading template...');
    const pdfBytes = await downloadPdf(url);

    // Load the PDF
    const pdfDoc = await PDFDocument.load(pdfBytes);
    const form = pdfDoc.getForm();
    const fields = form.getFields();

    console.log(`Found ${fields.length} fields. Auto-filling with field names...`);

    // Auto-fill all fields with their names
    fields.forEach(field => {
      const name = field.getName();
      try {
        if (field.constructor.name === 'PDFTextField') {
          field.setText(name);
        } else if (field.constructor.name === 'PDFCheckBox') {
          // Skip or handle checkboxes differently if needed
        }
        console.log(`Filled: ${name}`);
      } catch (e) {
        console.log(`Could not fill ${name}: ${e.message}`);
      }
    });

    // Flatten the form to make fillings permanent/visible
    form.flatten();

    // Save the filled PDF
    const outputBytes = await pdfDoc.save();
    fs.writeFileSync('manual_filled_js.pdf', outputBytes);
    console.log('Saved filled PDF as manual_filled_js.pdf');

  } catch (error) {
    console.error('Error:', error);
  }
}

fillManual();