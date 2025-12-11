const OpenAI = require('openai');
const { getActiveLLMConfig } = require('../utils/db');

function getActiveLLMClient() {
    const config = getActiveLLMConfig();
    
    if (!config) {
        console.log('No active LLM configuration found. Using fallback mock.');
        return null;
    }

    if (config.provider === 'openai') {
        return new OpenAI({
            apiKey: config.api_key,
            baseURL: config.base_url || undefined
        });
    }
    
    // Add other providers here (anthropic, etc.)
    console.log(`Provider ${config.provider} not yet supported.`);
    return null;
}

async function generateContent(prompt, model = null) {
    const client = getActiveLLMClient();
    const config = getActiveLLMConfig();
    
    if (!client || !config) {
        console.log('No active LLM configuration found. Returning mock content.');
        return "# Mock Content\n\nThis is generated content for the MVP test.\n\nConfigure your LLM settings in the dashboard to use AI-powered content generation.";
    }

    try {
        const completion = await client.chat.completions.create({
            messages: [{ role: 'user', content: prompt }],
            model: model || config.model || 'gpt-4o',
        });
        return completion.choices[0].message.content;
    } catch (e) {
        console.error('LLM Error:', e.message);
        console.log('Falling back to mock content due to API error.');
        return "# Mock Content (Fallback)\n\nThis content was generated because the LLM API failed. \n\nError: " + e.message + "\n\nIdea: " + prompt;
    }
}

module.exports = { generateContent };
