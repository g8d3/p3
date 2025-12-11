import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'

dotenv.config()

const app = express()

// Middleware
app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}))

app.use(express.json())

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

// Mock GraphQL endpoint for now
app.get('/graphql', (req, res) => {
  res.json({ 
    message: 'GraphQL Playground would be here',
    status: 'ready for GraphQL integration'
  })
})

// In-memory storage for demo purposes
const tables: any[] = []

// Tables API endpoints
app.get('/api/tables', (req, res) => {
  res.json({ tables })
})

app.post('/api/tables', (req, res) => {
  const newTable = { ...req.body, createdAt: new Date().toISOString() }
  tables.push(newTable)
  res.json(newTable)
})

app.delete('/api/tables/:id', (req, res) => {
  const index = tables.findIndex((t: any) => t.id === req.params.id)
  if (index !== -1) {
    const deletedTable = tables.splice(index, 1)
    res.json(deletedTable[0])
  } else {
    res.status(404).json({ error: 'Table not found' })
  }
})

// Test AI connection endpoint
app.post('/test-ai-connection', async (req, res) => {
  const { apiKey, model = 'gpt-4', baseUrl = 'https://api.openai.com/v1' } = req.body
  
  if (!apiKey) {
    return res.status(400).json({ error: 'API key is required' })
  }

  try {
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model,
        messages: [
          {
            role: 'user',
            content: 'Hello, this is a connection test. Please respond with "Connection successful".'
          }
        ],
        max_tokens: 10,
      }),
    })

    if (response.ok) {
      const data = await response.json() as any
      res.json({ 
        success: true, 
        message: 'Connection successful',
        model: model,
        usage: data.usage || {}
      })
    } else {
      const errorData = await response.text()
      res.status(response.status).json({ 
        success: false, 
        error: `API Error: ${errorData}` 
      })
    }
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error' 
    })
  }
})

// Mock API endpoints
app.post('/graphql', (req, res) => {
  const { query } = req.body
  console.log('Received GraphQL query:', query)
  
  // Mock responses for common queries
  if (query.includes('projects')) {
    res.json({
      data: {
        projects: [
          {
            id: '1',
            name: 'Demo Project',
            description: 'A demonstration project',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          }
        ]
      }
    })
  } else if (query.includes('generateAISchema')) {
    res.json({
      data: {
        generateAISchema: {
          recommendedSchema: [
            {
              name: 'users',
              description: 'User accounts and authentication',
              fields: [
                { id: 'id', name: 'id', type: 'String', required: true, description: 'Primary key' },
                { id: 'email', name: 'email', type: 'Email', required: true, description: 'User email address' },
                { id: 'name', name: 'name', type: 'String', required: true, description: 'Full name' }
              ]
            }
          ],
          reasoning: 'Generated schema based on common patterns for user management',
          confidence: 0.85
        }
      }
    })
  } else {
    res.json({
      data: {
        message: 'GraphQL query processed'
      }
    })
  }
})

const PORT = process.env.PORT || 4000

app.listen(PORT, () => {
  console.log(`🚀 Backend server ready at http://localhost:${PORT}`)
  console.log(`📊 Health check: http://localhost:${PORT}/health`)
  console.log(`🔗 GraphQL endpoint: http://localhost:${PORT}/graphql`)
})
