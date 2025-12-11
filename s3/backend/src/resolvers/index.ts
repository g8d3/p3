import datasources from '../data'
import AIService from '../services/AIService'

const resolvers: any = {
  Query: {
    projects: async () => {
      return await datasources.project.getAll()
    },
    
    project: async (_, { id }) => {
      return await datasources.project.getById(id)
    },
    
    tables: async (_, { projectId }) => {
      return await datasources.table.getByProjectId(projectId)
    },
    
    workflows: async (_, { projectId }) => {
      return await datasources.workflow.getByProjectId(projectId)
    },
    
    workflow: async (_, { id }) => {
      return await datasources.workflow.getById(id)
    }
  },

  Mutation: {
    createProject: async (_, { input }) => {
      return await datasources.project.create(input)
    },
    
    updateProject: async (_, { id, name, description }) => {
      return await datasources.project.update(id, { name, description })
    },
    
    deleteProject: async (_, { id }) => {
      return await datasources.project.delete(id)
    },

    createTable: async (_, { projectId, input }) => {
      return await datasources.table.create(projectId, input)
    },
    
    updateTable: async (_, { id, name, description }) => {
      return await datasources.table.update(id, { name, description })
    },
    
    deleteTable: async (_, { id }) => {
      return await datasources.table.delete(id)
    },

    createWorkflow: async (_, { projectId, input }) => {
      return await datasources.workflow.create(projectId, input)
    },
    
    updateWorkflow: async (_, { id, name, description, nodes, edges }) => {
      const updateData: any = {}
      if (name) updateData.name = name
      if (description) updateData.description = description
      if (nodes) updateData.nodes = nodes
      if (edges) updateData.edges = edges
      
      return await datasources.workflow.update(id, updateData)
    },
    
    deleteWorkflow: async (_, { id }) => {
      return await datasources.workflow.delete(id)
    },

    generateAISchema: async (_, { input }) => {
      try {
        await AIService.initialize()
        const suggestion = await AIService.generateDatabaseSchema(input.description)
        return suggestion
      } catch (error) {
        throw new Error(`AI Schema Generation failed: ${error}`)
      }
    },

    getAIWorkflowSuggestions: async (_, { projectId }) => {
      try {
        await AIService.initialize()
        const project = await datasources.project.getById(projectId)
        const tables = await datasources.table.getByProjectId(projectId)
        const tablesWithFields = tables.map(table => ({
          ...table,
          // Add empty fields array for now - in real implementation would fetch fields
          fields: []
        }))
        
        const suggestions = await AIService.suggestWorkflows(project || { id: '', name: '', description: '' }, tablesWithFields)
        return suggestions
      } catch (error) {
        throw new Error(`AI Workflow Suggestions failed: ${error}`)
      }
    }
  },

  Subscription: {
    workflowExecution: {
      subscribe: async (_, { workflowId }) => {
        // Implementation would use WebSocket subscriptions
        return null
      }
    },
    
    projectUpdates: {
      subscribe: async (_, { projectId }) => {
        // Implementation would use WebSocket subscriptions
        return null
      }
    }
  },

  Project: {
    tables: async (parent) => {
      return await datasources.table.getByProjectId(parent.id)
    },
    
    workflows: async (parent) => {
      return await datasources.workflow.getByProjectId(parent.id)
    }
  },

  Table: {
    fields: async (parent) => {
      return await datasources.field.getByTableId(parent.id)
    }
  }
}

export default resolvers
