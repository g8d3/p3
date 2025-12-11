"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const apollo_server_express_1 = require("apollo-server-express");
const cors_1 = __importDefault(require("cors"));
const dotenv_1 = __importDefault(require("dotenv"));
const typeDefs_1 = __importDefault(require("./typeDefs"));
const resolvers_1 = __importDefault(require("./resolvers"));
dotenv_1.default.config();
async function startServer() {
    const app = (0, express_1.default)();
    // Middleware
    app.use((0, cors_1.default)({
        origin: process.env.FRONTEND_URL || 'http://localhost:3000',
        credentials: true
    }));
    app.use(express_1.default.json());
    // Health check endpoint
    app.get('/health', (req, res) => {
        res.json({ status: 'ok', timestamp: new Date().toISOString() });
    });
    // Apollo Server setup
    const server = new apollo_server_express_1.ApolloServer({
        typeDefs: typeDefs_1.default,
        resolvers: resolvers_1.default,
        introspection: process.env.NODE_ENV !== 'production',
        playground: process.env.NODE_ENV !== 'production',
        context: ({ req, res }) => {
            return {
                req,
                res,
            };
        }
    });
    await server.start();
    // Apply GraphQL middleware
    server.applyMiddleware({
        app,
        path: '/graphql',
        cors: false // We already configured CORS above
    });
    const PORT = process.env.PORT || 4000;
    app.listen(PORT, () => {
        console.log(`🚀 Server ready at http://localhost:${PORT}/graphql`);
        console.log(`📊 GraphQL Playground: http://localhost:${PORT}/graphql`);
    });
}
// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('👋 Shutting down server...');
    process.exit(0);
});
process.on('SIGTERM', () => {
    console.log('👋 Shutting down server...');
    process.exit(0);
});
startServer().catch(error => {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
});
