# 🚀 Development Workflow Guide

## Quick Commands

```bash
# Start development server in background with logging
npm run dev:background

# View server logs in real-time
npm run dev:logs

# Check server status
npm run dev:status

# Stop background server
npm run dev:stop

# Regular development (foreground)
npm run dev
```

## 📋 Environment Files

### Two Files Only
```
.env.example    ← Template with where-to-get docs (Git ✅)
.env.local     ← Your actual secrets (Git ❌)
```

### Loading Order (Next.js)
1. `.env.local` - Your secrets (highest priority)
2. `.env` - Default values
3. `.env.development` - Dev-specific (optional)
4. `.env.production` - Prod-specific (optional)

Note: `.env.example` is **NOT** loaded by Next.js - it's documentation.

## 🖥 Browser Testing with agent-browser

### Available Commands
```bash
# Navigate to a page
agent-browser open http://localhost:3000

# Take screenshot
agent-browser screenshot /tmp/screenshot.png

# Get page information
agent-browser get url
agent-browser get text
agent-browser get title

# Navigate between pages
agent-browser back
agent-browser forward
agent-browser reload

# Interact with elements
agent-browser click "text=Buy Skill"
agent-browser type "input[type='email']" "test@example.com"
agent-browser eval "document.querySelector('.btn').click()"

# Check for console errors
agent-browser eval "console.error('test')"
```

### Example Testing Workflow
```bash
# 1. Start server (background)
npm run dev:background

# 2. Open browser
agent-browser open http://localhost:3000

# 3. Navigate to skills
agent-browser open http://localhost:3000/skills

# 4. Take screenshot
agent-browser screenshot /tmp/skills-page.png

# 5. Check for client errors
agent-browser eval "window.location.href"

# 6. View server logs
npm run dev:logs

# 7. Test API endpoints
curl http://localhost:3000/api/skills/featured
```

## 📝 Server Logs

### Background Server with Logging
- Logs are written to: `dev-server-logs/server-<timestamp>.log`
- PID is tracked in: `dev-server-logs/server.pid`
- New log file created each restart

### Log Management
```bash
# View live logs
tail -f dev-server-logs/server-$(ls -t dev-server-logs/server-*.log 2>/dev/null | head -1)

# View recent logs
cat dev-server-logs/server-$(ls -t dev-server-logs/server-*.log 2>/dev/null | head -1) | tail -50

# Clean old logs
rm dev-server-logs/server-*.log  # Remove all logs
```

## 🐛 Debugging Workflow

### Finding Client Errors
```bash
# 1. Start server
npm run dev:background

# 2. Open with agent-browser
agent-browser connect localhost:3000 http://localhost:3000

# 3. Navigate and check
agent-browser open http://localhost:3000/skills
agent-browser eval "console.log('Checking for errors...')"

# 4. Check browser console
agent-browser eval "window.onerror"

# 5. Take screenshot for reference
agent-browser screenshot /tmp/error-state.png

# 6. Check server logs for related errors
npm run dev:logs | grep -i error
```

### Finding Server Errors
```bash
# 1. View logs
npm run dev:logs

# 2. Filter for errors
npm run dev:logs | grep -i "error\|exception\|fail"

# 3. Filter for warnings
npm run dev:logs | grep -i "warning"

# 4. Search for specific routes
npm run dev:logs | grep "/api/skills"
```

## 🔧 Configuration Files

### .gitignore
Updated to ignore:
- `*.log` - All log files
- `*.pid` - Process ID files
- `/dev-server-logs/` - Log directory

### .env.example
Contains:
- All required environment variables
- Where to get each variable (URLs)
- How to generate secrets (commands)
- Quick start commands
- Help sections (preserved per request)

## 🔄 Workflow Examples

### Quick Fix and Test Cycle
```bash
# 1. Make code changes
nano app/page.tsx

# 2. Server auto-recompiles (watching for changes)

# 3. Test with agent-browser
agent-browser open http://localhost:3000
agent-browser screenshot /tmp/fix-test.png

# 4. Check logs
npm run dev:logs | tail -10

# 5. Iterate
# Repeat from step 1
```

### Full Development Session
```bash
# Terminal 1: Server (background)
npm run dev:background
npm run dev:logs   # Watch logs

# Terminal 2: Code changes
vim app/page.tsx
# Or use VS Code

# Terminal 3: Browser testing
agent-browser open http://localhost:3000
agent-browser click "text=Search"
agent-browser type "input[name='search']" "AI"
agent-browser screenshot /tmp/search-results.png

# Check everything works together
```

## 📊 Monitoring

### Check Server Health
```bash
# Server status
npm run dev:status

# If not running, restart
npm run dev:stop && npm run dev:background

# Test endpoint
curl -I http://localhost:3000/api/health
```

### Monitor Performance
```bash
# Watch logs for slow responses
npm run dev:logs | grep "ms$"

# Look for HMR (Hot Module Replacement) issues
npm run dev:logs | grep -i "hmr\|compile"

# Check memory usage
ps aux | grep "next dev"
```

## 🎯 Tips for Efficient Development

1. **Use background server** - Keeps server running while editing code
2. **Monitor logs in separate terminal** - Real-time feedback
3. **Use agent-browser for navigation** - Faster than manual browser refresh
4. **Take screenshots** - Reference state when debugging
5. **Filter logs** - `npm run dev:logs | grep error`
6. **Kill stale processes** - `npm run dev:stop` before starting new
7. **Keep logs for debugging** - Don't clear unless disk full

## 🔧 Common Issues

### Server won't start
```bash
# Kill existing processes
pkill -f "next dev"
npm run dev:stop

# Check port 3000
lsof -i :3000

# Remove stale PID
rm -f dev-server-logs/server.pid
```

### agent-browser connection issues
```bash
# Ensure server is running
npm run dev:status

# Use correct URL
agent-browser open http://localhost:3000  # Not /skills

# Reconnect if needed
agent-browser connect localhost:3000 http://localhost:3000
```

## 📄 Files Reference

| File | Purpose | Status |
|-------|---------|--------|
| `.env.example` | Template with help docs | ✅ Complete |
| `.env.local` | Your secrets (create manually) | ✅ Ready to fill |
| `.gitignore` | What to ignore | ✅ Updated |
| `package.json` | Scripts added | ✅ dev:*, build, start |
| `dev-server-logs/` | Server logs | ✅ Created when needed |

---

**Happy coding!** 🚀
