# s7

To install dependencies:

```bash
bun install
```

To run:

```bash
bun run index.ts
```

This project was created using `bun init` in bun v1.1.43. [Bun](https://bun.sh) is a fast all-in-one JavaScript runtime.

## AI Scraper Application - Complete Testing Suite

This is a comprehensive AI-powered web scraper application with full end-to-end testing.

### 🚀 Quick Start
```bash
# 1. Start your services (use your existing setup)
./pocketbase serve --http 0.0.0.0:8090 &
bun run dev &

# 2. Run tests (works with your running services)
./run-tests.sh
```

### 🧪 Testing Options
```bash
# Full test suite (requires running services)
./run-tests.sh

# API-only tests (no browser required)
bun run test

# Development server with auto-reload
./dev.sh

# Start Chrome CDP (optional, for full browser tests)
/usr/bin/google-chrome --headless --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 &
```

### 📋 Business Requirements Tested
- ✅ **User Authentication & Multi-user Support**
- ✅ **CRUD Operations** for all resources (AI models, browsers, scrapers, tests)
- ✅ **AI-Powered Scraping** with real CDP browser integration
- ✅ **Pipeline Transparency** - step-by-step execution logging
- ✅ **Testing System** - user-defined tests with full history
- ✅ **Error Handling** - graceful, non-disruptive error messages
- ✅ **Data Persistence** - everything saved to PocketBase
- ✅ **Real Implementation** - no mocks, actual scraping capabilities

### 🏗️ Architecture
- **Frontend**: Vanilla JS + Tailwind CSS (no frameworks for maximum control)
- **Backend**: Bun.js server with PocketBase
- **Browser Automation**: Puppeteer + Chrome CDP
- **AI Integration**: OpenAI API for code generation
- **Database**: PocketBase with real-time subscriptions
- **Testing**: Puppeteer CDP for comprehensive E2E tests

### 🎯 Key Features
- **Maximum User Control**: Full access to all internal processes
- **AI-Assisted Scraping**: Enter URL → AI analyzes → generates code → runs extraction
- **Step-by-Step Transparency**: See every action, decision, and result
- **Built-in Testing**: Create and run tests on your scrapers
- **Error History**: Complete audit trail of all operations
- **Multi-user**: Complete isolation between users
- **Scheduling**: Cron-based automated scraping
- **Data Sinks**: Export to webhooks, APIs, databases

### 🧪 Test Coverage
- User registration/login flow
- Configuration management (AI models, browsers, data sinks)
- Scraper creation and management
- AI discovery workflow
- Code generation and execution
- Testing system functionality
- Error handling and recovery
- Business requirement compliance
- UI responsiveness and accessibility

When all tests pass ✅, the application is **production-ready**! 🎉
