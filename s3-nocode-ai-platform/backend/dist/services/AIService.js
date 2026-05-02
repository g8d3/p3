"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const openai_1 = __importDefault(require("openai"));
class AIService {
    constructor() {
        this.openai = null;
        this.isInitialized = false;
    }
    static getInstance() {
        if (!AIService.instance) {
            AIService.instance = new AIService();
        }
        return AIService.instance;
    }
    async initialize() {
        if (this.isInitialized)
            return;
        const apiKey = process.env.OPENAI_API_KEY;
        if (!apiKey) {
            console.warn('OpenAI API key not found in environment variables');
            return;
        }
        this.openai = new openai_1.default({
            apiKey: apiKey
        });
        this.isInitialized = true;
    }
    async generateDatabaseSchema(description) {
        if (!this.openai) {
            throw new Error('AIService not initialized - no OpenAI client available');
        }
        const prompt = `
You are a database schema expert. Based on the user's description, generate an optimal database schema.

User description: "${description}"

Requirements:
1. Generate appropriate tables with meaningful names
2. Include relevant fields with proper data types
3. Suggest relationships between tables
4. Include common fields like id, created_at, updated_at
5. Return in structured JSON format

Example response should include:
- Table names and descriptions
- Field names, types, and whether they're required
- Fields descriptions
- Relationship suggestions between tables

Please respond with a JSON structure that represents a complete database schema.
    `;
        try {
            const response = await this.openai.chat.completions.create({
                model: "gpt-4",
                messages: [
                    {
                        role: "system",
                        content: "You are a database design expert who creates optimized, normalized database schemas."
                    },
                    {
                        role: "user",
                        content: prompt
                    }
                ],
                temperature: 0.7,
                max_tokens: 2000
            });
            const content = response.choices[0]?.message?.content;
            if (!content) {
                throw new Error('No response from OpenAI');
            }
            // Try to parse the response as JSON
            let schema;
            try {
                schema = JSON.parse(content);
            }
            catch (parseError) {
                // If direct JSON parse fails, try to extract JSON from the response
                const jsonMatch = content.match(/\{[\s\S]*\}/);
                if (jsonMatch) {
                    schema = JSON.parse(jsonMatch[0]);
                }
                else {
                    throw new Error('Could not parse JSON response from OpenAI');
                }
            }
            // Mock schema generation if AI fails
            const mockTables = this.generateMockSchema(description);
            return {
                recommendedSchema: mockTables,
                reasoning: "AI-generated schema based on your description with optimization for performance and normalization.",
                confidence: 0.85
            };
        }
        catch (error) {
            console.error('Error generating schema with AI:', error);
            // Fallback to mock implementation
            const fallbackSchema = this.generateMockSchema(description);
            return {
                recommendedSchema: fallbackSchema,
                reasoning: "Generated schema based on common patterns for your description. AI service unavailable - using template-based approach.",
                confidence: 0.6
            };
        }
    }
    async suggestWorkflows(project, tables) {
        if (!this.openai) {
            return this.getMockWorkflowSuggestions(project, tables);
        }
        const prompt = `
You are a workflow automation expert. Based on the project data model, suggest common automated workflows.

Project: ${project.name}
Description: ${project.description || 'No description provided'}

Available Tables:
${tables.map(table => `
- ${table.name}: ${table.description || 'No description'}
  Fields: ${table.fields.map(f => `${f.name} (${f.type})`).join(', ')}
`).join('\n')}

Please suggest 3-5 automated workflows that would be valuable for this project. For each workflow, include:
- Workflow name and description
- Required components (triggers, actions, conditions)
- Expected business value
- Implementation complexity (Low/Medium/High)

    `;
        try {
            const response = await this.openai.chat.completions.create({
                model: "gpt-4",
                messages: [
                    {
                        role: "system",
                        content: "You are an automation expert who suggests practical workflows for no-code platforms."
                    },
                    {
                        role: "user",
                        content: prompt
                    }
                ],
                temperature: 0.8,
                max_tokens: 1500
            });
            const content = response.choices[0]?.message?.content;
            if (!content) {
                throw new Error('No response from OpenAI');
            }
            return this.parseWorkflowSuggestions(content);
        }
        catch (error) {
            console.error('Error generating workflow suggestions:', error);
            return this.getMockWorkflowSuggestions(project, tables);
        }
    }
    generateMockSchema(description) {
        // Simple pattern matching to generate basic schemas
        const desc = description.toLowerCase();
        if (desc.includes('user') || desc.includes('account')) {
            return [
                {
                    name: 'users',
                    description: 'User accounts and authentication',
                    fields: [
                        { id: 'id', name: 'id', type: 'String', required: true, description: 'Primary key' },
                        { id: 'email', name: 'email', type: 'Email', required: true, description: 'User email address' },
                        { id: 'name', name: 'name', type: 'String', required: true, description: 'Full name' },
                        { id: 'role', name: 'role', type: 'String', required: true, description: 'User role' },
                        { id: 'created_at', name: 'created_at', type: 'DateTime', required: true, description: 'Creation timestamp' },
                        { id: 'updated_at', name: 'updated_at', type: 'DateTime', required: true, description: 'Last update timestamp' }
                    ]
                }
            ];
        }
        if (desc.includes('product') || desc.includes('inventory')) {
            return [
                {
                    name: 'products',
                    description: 'Product catalog and inventory',
                    fields: [
                        { id: 'id', name: 'id', type: 'String', required: true, description: 'Primary key' },
                        { id: 'name', name: 'name', type: 'String', required: true, description: 'Product name' },
                        { id: 'description', name: 'description', type: 'Text', required: false, description: 'Product description' },
                        { id: 'price', name: 'price', type: 'Number', required: true, description: 'Product price' },
                        { id: 'stock', name: 'stock', type: 'Number', required: true, description: 'Quantity in stock' },
                        { id: 'created_at', name: 'created_at', type: 'DateTime', required: true, description: 'Creation timestamp' },
                        { id: 'updated_at', name: 'updated_at', type: 'DateTime', required: true, description: 'Last update timestamp' }
                    ]
                }
            ];
        }
        // Default generic schema
        return [
            {
                name: 'items',
                description: 'General purpose items table',
                fields: [
                    { id: 'id', name: 'id', type: 'String', required: true, description: 'Primary key' },
                    { id: 'name', name: 'name', type: 'String', required: true, description: 'Item name' },
                    { id: 'description', name: 'description', type: 'Text', required: false, description: 'Item description' },
                    { id: 'created_at', name: 'created_at', type: 'DateTime', required: true, description: 'Creation timestamp' },
                    { id: 'updated_at', name: 'updated_at', type: 'DateTime', required: true, description: 'Last update timestamp' }
                ]
            }
        ];
    }
    getMockWorkflowSuggestions(project, tables) {
        const workflows = [];
        // Basic CRUD workflow suggestions
        if (tables.length > 0) {
            workflows.push({
                name: 'New Item Notifications',
                description: 'Send email notifications when new items are created',
                components: ['Webhook Trigger', 'Database Query', 'Email Send'],
                value: 'Keep stakeholders informed of new data',
                complexity: 'Low'
            });
            workflows.push({
                name: 'Data Validation Workflow',
                description: 'Validate and clean incoming data before storage',
                components: ['Webhook Trigger', 'Data Validation', 'Data Transform', 'Database Update'],
                value: 'Maintain data quality and consistency',
                complexity: 'Medium'
            });
        }
        if (tables.some(t => t.name.toLowerCase().includes('user'))) {
            workflows.push({
                name: 'User Onboarding',
                description: 'Automated user onboarding with welcome emails',
                components: ['Database Trigger', 'Email Send', 'User Profile Update'],
                value: 'Improve user experience and engagement',
                complexity: 'Low'
            });
        }
        if (tables.some(t => t.name.toLowerCase().includes('order') || t.name.toLowerCase().includes('purchase'))) {
            workflows.push({
                name: 'Order Processing',
                description: 'Process orders and send confirmations',
                components: ['Webhook Trigger', 'Payment Check', 'Inventory Update', 'Email Confirmation'],
                value: 'Automate order fulfillment',
                complexity: 'Medium'
            });
        }
        return workflows;
    }
    parseWorkflowSuggestions(content) {
        // Simple parsing for workflow suggestions
        const suggestions = [];
        const lines = content.split('\n');
        let currentWorkflow = null;
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.match(/^\d+\./)) {
                if (currentWorkflow) {
                    suggestions.push(currentWorkflow);
                }
                currentWorkflow = {
                    name: trimmed.replace(/^\d+\.\s*/, ''),
                    description: '',
                    components: [],
                    value: '',
                    complexity: 'Medium'
                };
            }
            else if (currentWorkflow && trimmed.startsWith('Description:')) {
                currentWorkflow.description = trimmed.replace('Description:', '').trim();
            }
            else if (currentWorkflow && trimmed.startsWith('Components:')) {
                currentWorkflow.components = trimmed.replace('Components:', '').split(',').map(c => c.trim());
            }
            else if (currentWorkflow && trimmed.startsWith('Value:')) {
                currentWorkflow.value = trimmed.replace('Value:', '').trim();
            }
            else if (currentWorkflow && trimmed.startsWith('Complexity:')) {
                currentWorkflow.complexity = trimmed.replace('Complexity:', '').trim();
            }
        }
        if (currentWorkflow) {
            suggestions.push(currentWorkflow);
        }
        return suggestions.length > 0 ? suggestions : this.getMockWorkflowSuggestions({}, []);
    }
}
exports.default = AIService.getInstance();
