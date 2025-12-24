
import { OpenAI } from 'openai';

export async function generateScrapingCode(
  url: string, 
  target: { title: string, description: string, type: string },
  aiConfig: { apiKey: string, apiUrl: string, modelId: string }
) {
  const openai = new OpenAI({
    apiKey: aiConfig.apiKey,
    baseURL: aiConfig.apiUrl
  });

  const prompt = `
Write a typescript function named "extract" that uses Puppeteer.
It should take a Puppeteer Page object as input and return the extracted data.
Target: ${target.title} (${target.description}, Type: ${target.type})
URL: ${url}

The function should be robust, handle potential missing elements, and return a JSON-serializable object or array.
Also write a test function named "testExtract" that takes the extracted data and returns { success: boolean, logs: string[] }.

Return ONLY the code, no markdown blocks.
Example structure:
async function extract(page) { ... }
async function testExtract(data) { ... }
`;

  const response = await openai.chat.completions.create({
    model: aiConfig.modelId,
    messages: [{ role: 'user', content: prompt }]
  });

  return response.choices[0].message.content;
}
