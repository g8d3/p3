const OpenAI = require('openai');

// Initialize OpenAI client
const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY || 'mock-key',
});

async function generateContent(prompt, model = 'gpt-4o') {
    if (!process.env.OPENAI_API_KEY) {
        console.log('No OPENAI_API_KEY found. Returning mock content.');
        return "# Mock Content\n\nThis is generated content for the MVP test.";
    }

    try {
        const completion = await openai.chat.completions.create({
            messages: [{ role: 'user', content: prompt }],
            model: model,
        });
        return completion.choices[0].message.content;
    } catch (e) {
        console.error('LLM Error:', e.message);
        console.log('Falling back to mock content due to API error.');
        return "# Mock Content (Fallback)\n\nThis content was generated because the LLM API quota is exceeded or failed. \n\nIdea: " + prompt;
    }
}

module.exports = { generateContent };
