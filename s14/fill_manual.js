const { PDFDocument, PDFName } = require('pdf-lib');
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

async function verifyFields(formType = 'f5472') {
  try {
    const templatePath = `${formType}.pdf`;
    const outputPdfPath = `verified_${formType}.pdf`;
    const url = `https://www.irs.gov/pub/irs-pdf/${formType}.pdf`;
    let pdfBytes;

    console.log(`Using template file: ${templatePath}`);
    if (fs.existsSync(templatePath)) {
      console.log('Loading template from local file...');
      pdfBytes = fs.readFileSync(templatePath);
    } else {
      console.log('Downloading template...');
      pdfBytes = await downloadPdf(url);
      fs.writeFileSync(templatePath, pdfBytes);
      console.log('Saved template locally as f5472.pdf');
    }

    // Load the PDF
    const pdfDoc = await PDFDocument.load(pdfBytes);
    const form = pdfDoc.getForm();
    const fields = form.getFields();

    console.log(`Found ${fields.length} fields. Inferring labels and verifying...`);

    // No hardcoded mappings - using inference and user-edited CSV
        'f1_1': 'EIN',
        'f1_3': 'Tax Year',
        'f1_5': 'Name of reporting corporation',
        'f1_6': 'Address',
        'f1_7': 'City, State, ZIP',
        'f1_8': 'Total assets',
        'f1_9': 'Principal business activity',
        'f1_10': 'Principal business activity code',
        'f1_11': 'Total value of gross payments',
        'f1_12': 'Total number of Forms 5472',
        'f1_13': 'Total value of gross payments on all Forms 5472',
        'f1_14': 'Total number of Parts VIII attached',
        'f1_15': 'Country of incorporation',
        'f1_16': 'Date of incorporation',
        'f1_17': 'Country(ies) under whose laws the reporting corporation files',
        'f1_18': 'Principal country(ies) where business is conducted',
        'f1_19': 'Name of related party',
        'f1_20': 'Address of related party',
        'f1_21': 'City, state, ZIP of related party',
        'f1_22': 'Country of related party',
        'f1_23': 'U.S. taxpayer ID number of related party',
        'f1_24': 'Foreign tax ID number of related party',
        'f1_25': 'Principal business activity of related party',
        'f1_26': 'Principal business activity code of related party',
        'f1_27': 'Percentage of ownership',
        'f1_28': 'Type of related party',
        'f1_29': 'Relationship',
        'f1_30': 'Amount of transactions',
        'f1_31': 'Description of transactions',
        'f1_32': 'Balance at end of year',
        'f1_33': 'Highest balance during year',
        'f1_34': 'Interest paid',
        'f1_35': 'Interest received',
        'f1_36': 'Principal payments',
        'f1_37': 'Principal receipts',
        'f1_38': 'Other payments',
        'f1_39': 'Other receipts',
        'f1_40': 'Total payments',
        'f1_41': 'Total receipts',
        'f1_42': 'Balance at beginning of year',
        'f1_43': 'Additions during year',
        'f1_44': 'Deductions during year',
        'f1_45': 'Balance at end of year',
        'f1_46': 'Description of property',
        'f1_47': 'FMV at acquisition',
        'f2_1': 'Sales of stock in trade',
        'f2_2': 'Sales of tangible personal property',
        'f2_3': 'Sales of property rights',
        'f2_4': 'Platform contribution transaction payments',
        'f2_5': 'Cost sharing payments',
        'f2_6': 'Compensation paid for technical, managerial, engineering, construction, or like services',
        'f2_7': 'Commissions paid',
        'f2_8': 'Rents, royalties, and license fees paid',
        'f2_9': 'Purchases of stock in trade',
        'f2_10': 'Purchases of tangible personal property',
        'f2_11': 'Purchases of property rights',
        'f2_12': 'Platform contribution transaction receipts',
        'f2_13': 'Cost sharing receipts',
        'f2_14': 'Compensation received for technical, managerial, engineering, construction, or like services',
        'f2_15': 'Commissions received',
        'f2_16': 'Rents, royalties, and license fees received',
        'f2_17': 'Amounts borrowed',
        'f2_18': 'Amounts loaned',
        'f2_19': 'Interest paid',
        'f2_20': 'Interest received',
        'f2_21': 'Amounts paid for research and development',
        'f2_22': 'Amounts received for research and development',
        'f2_23': 'Amounts paid for advertising and promotion',
        'f2_24': 'Amounts received for advertising and promotion',
        'f2_25': 'Amounts paid for management fees',
        'f2_26': 'Amounts received for management fees',
        'f2_27': 'Amounts paid for legal fees',
        'f2_28': 'Amounts received for legal fees',
        'f2_29': 'Amounts paid for accounting fees',
        'f2_30': 'Amounts received for accounting fees',
        'f2_31': 'Amounts paid for financial services',
        'f2_32': 'Amounts received for financial services',
        'f2_33': 'Amounts paid for insurance premiums',
        'f2_34': 'Amounts received for insurance premiums',
        'f2_35': 'Amounts paid for other services',
        'f2_36': 'Amounts received for other services',
        'f2_37': 'Amounts paid for other transactions',
        'f2_38': 'Amounts received for other transactions',
        'f2_39': 'Total amounts paid',
        'f2_40': 'Total amounts received',
        'f3_1': 'Description of transaction',
        'f3_2': 'Amount of transaction',
        'f3_3': 'Code',
        'f3_4': 'Description of transaction',
        'f3_5': 'Amount of transaction',
        'f3_6': 'Code',
        'f3_7': 'Description of transaction',
        'f3_8': 'Amount of transaction',
        'f3_9': 'Code',
        'f3_10': 'Description of transaction',
        'f3_11': 'Amount of transaction',
        'f3_12': 'Code',
        'f3_13': 'Description of transaction',
        'f3_14': 'Amount of transaction',
        'f3_15': 'Code',
        'f3_16': 'Description of transaction',
        'f3_17': 'Amount of transaction',
        'f3_18': 'Code',
        'c1_1': 'Consolidated filing',
        'c1_2': 'Initial year filing',
        'c1_3': 'Foreign person owns at least 50% of stock',
        'c1_4': 'Foreign person owns at least 50% of voting power',
        'c1_5': 'Foreign person owns at least 50% of value',
        'c2_1': 'Related party is a foreign/U.S. person',
        'c2_2': 'Related party owns at least 50% of stock',
        'c2_3': 'Related party owns at least 50% of voting power',
        'c2_4': 'Related party owns at least 50% of value',
        'c2_5': 'Check if amounts are from related party',
        'c2_6': 'Check if amounts are to related party',
        'c2_7': 'Check if other transactions',
        'c3_1': 'Category 1a/1b',
        'c3_2': 'Category 2a/2b',
        'c3_3': 'Category 3a/3b',
        'c3_4': 'Category 4a/4b',
        'c3_5': 'Category 5a/5b',
        'c3_6': 'Category 6a/6b',
        'c3_7': 'Category 7a/7b',
        'c3_8': 'Category 8a/8b',
        'c3_9': 'Category 9a/9b',
        'c3_10': 'Category 10a/10b',
        'c3_11': 'Category 11a/11b',
        'c3_12': 'Category 12a/12b',
        'c2_12': 'Check if Part VIII is attached',
      },
      f1120: {
        'f1_1': 'Name of corporation',
        'f1_2': 'Employer identification number',
        'f1_3': 'Principal business location',
        // Add more for f1120 as needed
      }
    };

    // Load labels from CSV if exists (user-corrected labels)
    const labelMap = {};
    if (fs.existsSync('fields.csv')) {
      const csvContent = fs.readFileSync('fields.csv', 'utf8');
      const lines = csvContent.split('\n');
      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',');
        if (parts.length >= 2) {
          const label = parts[0].replace(/"/g, '');
          const fieldName = parts[1].replace(/"/g, '');
          labelMap[fieldName] = label;
        }
      }
      console.log('Loaded labels from existing fields.csv');
    }

    const csvRows = ['Label,Field Name,Verified'];
    fields.forEach(field => {
      const name = field.getName();
      // Extract short field name (e.g., f1_19 from ...f1_19[0])
      const parts = name.split('.');
      const lastPart = parts[parts.length - 1];
      const shortName = lastPart.replace(/\[.*\]$/, ''); // Remove [0] etc.

      // Get label: from CSV if available, else infer from short name
      let label = labelMap[name];
      let verified = 'VERIFIED';
      if (label === undefined) {
        // Inference logic: basic transformation for human readability
        label = shortName.replace(/_/g, ' ').replace(/^f/, 'Field ').replace(/^c/, 'Checkbox ');
        verified = 'MISSING'; // Indicates inferred, not verified
      }

      csvRows.push(`"${label}","${name}","${verified}"`);

      // Fill PDF with the label or VERIFIED/MISSING
      try {
        if (field.constructor.name === 'PDFTextField') {
          field.setText(label.length <= 10 ? label : verified); // Use label if short, else VERIFIED/MISSING
        } else if (field.constructor.name === 'PDFCheckBox') {
          if (verified === 'VERIFIED') {
            field.check();
          } // Else leave unchecked
        }
      } catch (e) {
        console.log(`Could not fill ${name}: ${e.message}`);
      }
    });

    const csv = csvRows.join('\n');
    fs.writeFileSync('fields.csv', csv);
    console.log('Saved fields to fields.csv');

    // Flatten and save PDF
    form.flatten();
    const outputBytes = await pdfDoc.save();
    fs.writeFileSync(outputPdfPath, outputBytes);
    console.log(`Saved verified PDF to ${outputPdfPath}`);

  } catch (error) {
    console.error('Error:', error);
  }
}

verifyFields();