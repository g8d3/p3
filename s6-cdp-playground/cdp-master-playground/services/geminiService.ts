
import { GoogleGenAI } from "@google/genai";

// Fix: Initializing GoogleGenAI with the correct named parameter and direct API key access
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const explainProtocol = async (query: string) => {
  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-pro-preview',
      contents: `User Task: ${query}`,
      config: {
        // Persona and core logic should be in systemInstruction
        systemInstruction: "You are a Chrome DevTools Protocol expert. The user wants to know how to perform a task using CDP. Provide the domain, method, and a JSON example of the parameters. Also explain what the command does briefly. Format your response in Markdown with clear sections for 'Recommended Command' and 'Example Payload'.",
      }
    });
    // Fix: text is a property, not a method
    return response.text;
  } catch (error) {
    console.error("Gemini Error:", error);
    return "Failed to get AI assistance. Please check your network.";
  }
};

export const simulateCommandResponse = async (method: string, params: any) => {
  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `Simulate response for Method: ${method}, Parameters: ${JSON.stringify(params)}`,
      config: {
        systemInstruction: "You are a browser CDP engine. Simulate the JSON response for the following command. Return only the JSON object that would be returned by the Chrome debugger.",
        responseMimeType: "application/json",
      }
    });
    // Fix: text is a property, not a method
    return JSON.parse(response.text || '{}');
  } catch (error) {
    return { error: "Simulation failed", message: error instanceof Error ? error.message : String(error) };
  }
};
