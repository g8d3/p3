"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const data_1 = __importDefault(require("../data"));
const AIService_1 = __importDefault(require("../services/AIService"));
const resolvers = {
    Query: {
        projects: async () => {
            return await data_1.default.project.getAll();
        },
        project: async (_, { id }) => {
            return await data_1.default.project.getById(id);
        },
        tables: async (_, { projectId }) => {
            return await data_1.default.table.getByProjectId(projectId);
        },
        workflows: async (_, { projectId }) => {
            return await data_1.default.workflow.getByProjectId(projectId);
        },
        workflow: async (_, { id }) => {
            return await data_1.default.workflow.getById(id);
        }
    },
    Mutation: {
        createProject: async (_, { input }) => {
            return await data_1.default.project.create(input);
        },
        updateProject: async (_, { id, name, description }) => {
            return await data_1.default.project.update(id, { name, description });
        },
        deleteProject: async (_, { id }) => {
            return await data_1.default.project.delete(id);
        },
        createTable: async (_, { projectId, input }) => {
            return await data_1.default.table.create(projectId, input);
        },
        updateTable: async (_, { id, name, description }) => {
            return await data_1.default.table.update(id, { name, description });
        },
        deleteTable: async (_, { id }) => {
            return await data_1.default.table.delete(id);
        },
        createWorkflow: async (_, { projectId, input }) => {
            return await data_1.default.workflow.create(projectId, input);
        },
        updateWorkflow: async (_, { id, name, description, nodes, edges }) => {
            const updateData = {};
            if (name)
                updateData.name = name;
            if (description)
                updateData.description = description;
            if (nodes)
                updateData.nodes = nodes;
            if (edges)
                updateData.edges = edges;
            return await data_1.default.workflow.update(id, updateData);
        },
        deleteWorkflow: async (_, { id }) => {
            return await data_1.default.workflow.delete(id);
        },
        generateAISchema: async (_, { input }) => {
            try {
                await AIService_1.default.initialize();
                const suggestion = await AIService_1.default.generateDatabaseSchema(input.description);
                return suggestion;
            }
            catch (error) {
                throw new Error(`AI Schema Generation failed: ${error}`);
            }
        },
        getAIWorkflowSuggestions: async (_, { projectId }) => {
            try {
                await AIService_1.default.initialize();
                const project = await data_1.default.project.getById(projectId);
                const tables = await data_1.default.table.getByProjectId(projectId);
                const suggestions = await AIService_1.default.suggestWorkflows(project, tables);
                return suggestions;
            }
            catch (error) {
                throw new Error(`AI Workflow Suggestions failed: ${error}`);
            }
        }
    },
    Subscription: {
        workflowExecution: {
            subscribe: async (_, { workflowId }) => {
                // Implementation would use WebSocket subscriptions
                return null;
            }
        },
        projectUpdates: {
            subscribe: async (_, { projectId }) => {
                // Implementation would use WebSocket subscriptions
                return null;
            }
        }
    },
    Project: {
        tables: async (parent) => {
            return await data_1.default.table.getByProjectId(parent.id);
        },
        workflows: async (parent) => {
            return await data_1.default.workflow.getByProjectId(parent.id);
        }
    },
    Table: {
        fields: async (parent) => {
            return await data_1.default.field.getByTableId(parent.id);
        }
    }
};
exports.default = resolvers;
