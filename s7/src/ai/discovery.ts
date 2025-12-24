
import puppeteer from 'puppeteer-core';
import { OpenAI } from 'openai';

export async function discoverExtractionTargets(url: string, cdpUrl: string, aiConfig: { apiKey: string, apiUrl: string, modelId: string }) {
  const browser = await puppeteer.connect({ browserWSEndpoint: cdpUrl });
  const page = await browser.newPage();
  
  try {
    await page.goto(url, { waitUntil: 'networkidle2' });
    
    // Get some DOM info to help AI
    const pageData = await page.evaluate(() => {
      const getStructure = (el: Element, depth = 0): any => {
        if (depth > 3) return null;
        return {
          tag: el.tagName,
          id: el.id,
          classes: Array.from(el.classList).join(' '),
          children: Array.from(el.children).map(c => getStructure(c, depth + 1)).filter(Boolean)
        };
      };
      return {
        title: document.title,
        bodyStructure: getStructure(document.body)
      };
    });

    const openai = new OpenAI({
      apiKey: aiConfig.apiKey,
      baseURL: aiConfig.apiUrl
    });

    const response = await openai.chat.completions.create({
      model: aiConfig.modelId,
      messages: [
        {
          role: 'system',
          content: 'You are an expert web scraper assistant. Analyze the page structure and suggest extraction options.'
        },
        {
          role: 'user',
          content: `URL: ${url}\nPage Title: ${pageData.title}\nPage Structure: ${JSON.stringify(pageData.bodyStructure, null, 2)}\n\nSuggest 2-3 extraction options (e.g., list of items, product details, etc.). Return as JSON array of objects with "title", "description", and "type" (list or details).`
        }
      ],
      response_format: { type: 'json_object' }
    });

    const result = JSON.parse(response.choices[0].message.content || '{"options": []}');
    return result.options;
  } finally {
    await page.close();
    await browser.disconnect();
  }
}
