const OpenAI = require('openai');
const Anthropic = require('@anthropic-ai/sdk');
const cheerio = require('cheerio');

class LLMClient {
  constructor(config) {
    this.config = config;
    this.client = this.createClient();
  }

  createClient() {
    switch (this.config.provider.toLowerCase()) {
      case 'openai':
        return new OpenAI({
          apiKey: this.config.api_key,
          baseURL: this.config.base_url
        });
      case 'anthropic':
        return new Anthropic({
          apiKey: this.config.api_key,
          baseURL: this.config.base_url
        });
      default:
        throw new Error(`Unsupported LLM provider: ${this.config.provider}`);
    }
  }

  async analyzeAccessibility(axSnapshot) {
    // Convert AX tree to readable format
    const simplifiedAX = axSnapshot.slice(0, 50).map(node => ({
      role: node.role?.value,
      name: node.name?.value,
      description: node.description?.value,
      children: node.childIds?.length || 0
    }));

    const prompt = `Analyze this accessibility snapshot of a webpage and suggest what data could be scraped from it.
    The snapshot shows the page structure with roles, names, and descriptions. Identify lists, tables, or repeated content that contains data.

    Accessibility nodes (first 50):
    ${JSON.stringify(simplifiedAX, null, 2)}

    Respond ONLY with a valid JSON array of objects. Each object must have exactly these fields: 'selector' (CSS selector), 'description' (what it scrapes), 'dataType' (string/number/array).
    Focus on data that appears in lists or grids. Do not include any other text, explanations, or formatting. Just the JSON array.`;

    let response = await this.callLLM(prompt);
    if (typeof response !== 'string') {
      response = '';
    }
    // Strip markdown code blocks
    response = response.replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '').trim();

    try {
      // Try to parse the entire response as JSON
      return JSON.parse(response);
    } catch (error) {
      console.log('LLM response was not valid JSON after cleaning. Response:', response);
      // Try to extract JSON from the response
      const jsonMatch = response.match(/\[[\s\S]*?\]/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[0]);
        } catch (e) {
          console.log('Extracted JSON also invalid');
        }
      }
      // If all fails, return a default suggestion
      console.log('Using fallback suggestion');
      return [{
        selector: 'body',
        description: 'Main page content',
        dataType: 'text'
      }];
    }
  }

  async generateCode(html, suggestions, userConfirmation) {
    const prompt = `Generate the body of a JavaScript function that scrapes data from HTML using cheerio.

    The function should:
    - Take html as parameter
    - Load HTML with cheerio: const $ = cheerio.load(html);
    - Extract data based on: ${userConfirmation}
    - Return an array of objects (even if only one item)
    - Include basic error handling

    HTML sample:
    ${html.substring(0, 3000)}

    Suggestions: ${JSON.stringify(suggestions)}

    Respond with ONLY the function body code. No function declaration, no comments, no explanations. Just the code that goes inside the function.`;

    let code = await this.callLLM(prompt);
    // Strip markdown code blocks
    code = code.replace(/^```(?:javascript|js)?\s*/, '').replace(/\s*```$/, '').trim();
    return code;
  }

  async callLLM(prompt) {
    try {
      switch (this.config.provider.toLowerCase()) {
        case 'openai':
          const openaiResponse = await this.client.chat.completions.create({
            model: this.config.model,
            messages: [{ role: 'user', content: prompt }],
            max_tokens: 2000
          });
          return openaiResponse.choices[0].message.content;

        case 'anthropic':
          const anthropicResponse = await this.client.messages.create({
            model: this.config.model,
            max_tokens: 2000,
            messages: [{ role: 'user', content: prompt }]
          });
          return anthropicResponse.content[0].text;

        default:
          throw new Error(`Unsupported provider: ${this.config.provider}`);
      }
    } catch (error) {
      throw new Error(`LLM API call failed: ${error.message}`);
    }
  }
}

module.exports = LLMClient;