const { VM } = require('vm2');
const cheerio = require('cheerio');

class CodeGenerator {
  constructor(llmClient) {
    this.llmClient = llmClient;
  }

  async generateScrapingCode(html, suggestions, userConfirmation) {
    const code = await this.llmClient.generateCode(html, suggestions, userConfirmation);
    return this.validateAndCleanCode(code);
  }

  validateAndCleanCode(code) {
    // Basic validation: check if it has return
    if (!code.includes('return')) {
      throw new Error('Generated code does not appear to be valid scraping code');
    }

    // Wrap in function for testing
    const wrappedCode = `
      function scrapeData(html) {
        const cheerio = require('cheerio');
        const $ = cheerio.load(html);
        ${code}
      }
      scrapeData;
    `;

    try {
      // Test with sample HTML
      const testHtml = '<html><body><div class="item">Test</div></body></html>';
      const vm = new VM({
        sandbox: { cheerio, require: () => cheerio },
        timeout: 5000
      });

      const scrapeFunction = vm.run(wrappedCode);
      if (typeof scrapeFunction !== 'function') {
        throw new Error('Generated code does not define a valid function');
      }
      const result = scrapeFunction(testHtml);

      if (!Array.isArray(result)) {
        throw new Error('Generated code does not return an array');
      }

      return code;
    } catch (error) {
      throw new Error(`Code validation failed: ${error.message}`);
    }
  }

  async executeCode(code, html) {
    const wrappedCode = `
      function scrapeData(html) {
        const cheerio = require('cheerio');
        const $ = cheerio.load(html);
        ${code}
      }
      scrapeData(html);
    `;

    const vm = new VM({
      sandbox: { cheerio, html, require: () => cheerio },
      timeout: 10000
    });

    return vm.run(wrappedCode);
  }
}

module.exports = CodeGenerator;