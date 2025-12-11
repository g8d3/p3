import express from 'express'
import { ApolloServer } from 'apollo-server-express'
import cors from 'cors'
import dotenv from 'dotenv'
import typeDefs from './typeDefs'
import resolvers from './resolvers'

dotenv.config()

async function startServer() {
  const app = express()
  
  // Middleware
  app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true
  }))
  
  app.use(express.json())
  
  // Health check endpoint
  app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() })
  })

  // Apollo Server setup
  const server = new ApolloServer({
    typeDefs,
    resolvers,
    introspection: true,
    context: ({ req, res }) => ({ req, res })
  })

  await server.start()
  
  // Apply GraphQL middleware
  server.applyMiddleware({ 
    app: app as any, 
    path: '/graphql',
    cors: false // We already configured CORS above
  })

  // Health check endpoint
  app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() })
  })

  const PORT = process.env.PORT || 4000
  
  app.listen(PORT, () => {
    console.log(`🚀 Server ready at http://localhost:${PORT}`)
    console.log(`📊 GraphQL endpoint: http://localhost:${PORT}/graphql`)
  })
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('👋 Shutting down server...')
  process.exit(0)
})

process.on('SIGTERM', () => {
  console.log('👋 Shutting down server...')
  process.exit(0)
})

startServer().catch(error => {
  console.error('❌ Failed to start server:', error)
  process.exit(1)
})
