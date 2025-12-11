import { gql } from 'apollo-server-express'

const typeDefs = gql`
  scalar DateTime

  type Project {
    id: ID!
    name: String!
    description: String
    createdAt: DateTime!
    updatedAt: DateTime!
    tables: [Table!]!
    workflows: [Workflow!]!
  }

  type Table {
    id: ID!
    name: String!
    description: String
    fields: [Field!]!
    relationships: [Relationship!]!
    createdAt: DateTime!
    updatedAt: DateTime!
  }

  type Field {
    id: ID!
    name: String!
    type: String!
    required: Boolean!
    description: String
    defaultValue: String
    validation: ValidationRule
  }

  type ValidationRule {
    pattern: String
    minLength: Int
    maxLength: Int
    min: Float
    max: Float
  }

  type Relationship {
    id: ID!
    type: String!
    sourceTable: String!
    targetTable: String!
    sourceField: String!
    targetField: String!
  }

  type Workflow {
    id: ID!
    name: String!
    description: String
    nodes: [WorkflowNode!]!
    edges: [WorkflowEdge!]!
    isActive: Boolean!
    createdAt: DateTime!
    updatedAt: DateTime!
  }

  type WorkflowNode {
    id: ID!
    type: String!
    label: String!
    position: Position!
    config: JSON
    data: JSON
  }

  type WorkflowEdge {
    id: ID!
    source: String!
    target: String!
    sourceHandle: String
    targetHandle: String
    animated: Boolean
    style: JSON
  }

  type Position {
    x: Float!
    y: Float!
  }

  scalar JSON

  input CreateProjectInput {
    name: String!
    description: String
  }

  input CreateTableInput {
    name: String!
    description: String
    fields: [CreateFieldInput!]!
  }

  input CreateFieldInput {
    name: String!
    type: String!
    required: Boolean!
    description: String
    defaultValue: String
  }

  input CreateWorkflowInput {
    name: String!
    description: String
  }

  input AISchemaGenerationInput {
    description: String!
  }

  type AISuggestion {
    recommendedSchema: [Table!]!
    reasoning: String!
    confidence: Float!
  }

  type Query {
    projects: [Project!]!
    project(id: ID!): Project
    tables(projectId: ID!): [Table!]!
    workflows(projectId: ID!): [Workflow!]!
    workflow(id: ID!): Workflow
  }

  type Mutation {
    createProject(input: CreateProjectInput!): Project!
    updateProject(id: ID!, name: String, description: String): Project!
    deleteProject(id: ID!): Project!

    createTable(projectId: ID!, input: CreateTableInput!): Table!
    updateTable(id: ID!, name: String, description: String): Table!
    deleteTable(id: ID!): Table!

    createWorkflow(projectId: ID!, input: CreateWorkflowInput!): Workflow!
    updateWorkflow(id: ID!, name: String, description: String, nodes: [WorkflowNodeInput!], edges: [WorkflowEdgeInput!]): Workflow!
    deleteWorkflow(id: ID!): Workflow!

    generateAISchema(input: AISchemaGenerationInput!): AISuggestion!
    getAIWorkflowSuggestions(projectId: ID!): [JSON]!
  }

  input WorkflowNodeInput {
    id: ID!
    type: String!
    label: String!
    position: PositionInput!
    config: JSON
    data: JSON
  }

  input WorkflowEdgeInput {
    id: ID!
    source: String!
    target: String!
    sourceHandle: String
    targetHandle: String
    animated: Boolean
    style: JSON
  }

  input PositionInput {
    x: Float!
    y: Float!
  }

  type Subscription {
    workflowExecution(workflowId: ID!): WorkflowExecutionEvent!
    projectUpdates(projectId: ID!): Project!
  }

  type WorkflowExecutionEvent {
    id: ID!
    workflowId: ID!
    status: String!
    message: String
    timestamp: DateTime!
    nodeId: String
    error: String
  }

  type AIError {
    message: String!
    code: String!
    details: JSON
  }

  type AIExecution {
    id: ID!
    workflowId: ID!
    status: String!
    startTime: DateTime!
    endTime: DateTime
    steps: [ExecutionStep!]!
    errors: [AIError!]!
    result: JSON
  }

  type ExecutionStep {
    id: ID!
    nodeId: String!
    stepType: String!
    startTime: DateTime!
    endTime: DateTime
    input: JSON
    output: JSON
    error: String
    confidence: Float
    reasoning: String
  }
`

export default typeDefs
