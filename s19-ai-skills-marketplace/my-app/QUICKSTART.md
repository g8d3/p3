# 🚀 Quick Start Guide

## One Command to Start Everything

```bash
npm run dev:all:ngrok
```

This starts:
- ✅ Prisma database (embedded)
- ✅ Next.js dev server
- ✅ ngrok tunnel (for webhooks)
- ✅ All in background with logging

## View Everything Status

```bash
npm run dev:status
```

Shows:
- Server status (running/PID)
- Ngrok URL (for Polar webhook)
- Log file locations

## View Logs

```bash
# Server logs
npm run dev:logs

# Ngrok logs
cat ngrok-logs/ngrok-$(ls -t ngrok-logs/ngrok-*.log | head -1)
```

## Stop Everything

```bash
npm run dev:stop
```

Stops:
- Prisma database
- Next.js server
- Ngrok tunnel

---

## Workflow for Development

### 1. Start Everything (once)
```bash
npm run dev:all:ngrok
```

### 2. Get ngrok URL (auto-generated)
```bash
npm run ngrok:url
```

### 3. Update Polar Webhook (one-time setup)

1. Go to: https://polar.sh/dashboard/ooo/settings/webhooks
2. Create/Edit webhook
3. Webhook URL: `<ngrok-url>/api/payments/polar/webhook`
4. Events:
   - checkout.created
   - checkout.updated
   - order.created
5. Copy `POLAR_WEBHOOK_SECRET` from .env.local
6. Paste in Polar webhook settings

**Important**: Ngrok URL changes each time you restart. You only need to update Polar webhook once if you use a fixed domain (like ngrok Pro or localtunnel custom domain).

### 4. Test Payment Flow

```bash
# With agent-browser
agent-browser open http://localhost:3000/skills/some-skill
# Navigate to purchase, test payment

# With curl
curl http://localhost:3000/api/payments/polar/checkout \
  -H "Content-Type: application/json" \
  -d '{"skillId":"123","amount":100}'
```

---

## Quick Reference

| Command | What It Does |
|---------|---------------|
| `npm run dev:all:ngrok` | Start everything (DB + Server + ngrok) |
| `npm run dev:status` | Check all services status |
| `npm run dev:stop` | Stop all services |
| `npm run ngrok:url` | Get current ngrok URL |
| `npm run dev:logs` | View server logs |
| `npm run ngrok:background` | Start only ngrok |

---

## Notes

- First run: Update Polar webhook with ngrok URL
- After that: URL is stable as long as you don't restart ngrok
- Server auto-reloads on code changes
- Logs saved to `dev-server-logs/` and `ngrok-logs/`

---

## Troubleshooting

### Ngrok not starting?
```bash
# Check if ngrok is installed
which ngrok

# Install if needed
brew install ngrok  # Mac
choco install ngrok  # Windows
```

### Webhook not working?
```bash
# Check ngrok logs
cat ngrok-logs/ngrok-*.log

# Verify URL is correct
npm run ngrok:url

# Check webhook secret matches .env.local
grep POLAR_WEBHOOK_SECRET .env.local
```

### Database connection error?
```bash
# Check Prisma is running
ps aux | grep prisma

# If not, restart everything
npm run dev:stop && npm run dev:all:ngrok
```

---

**One command. Done.** 🎉
