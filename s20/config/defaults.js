export const config = {
  // Chrome DevTools Protocol
  chrome: {
    port: parseInt(process.env.CHROME_PORT) || 9222,
    host: process.env.CHROME_HOST || 'localhost',
    reconnect: {
      maxAttempts: 5,
      baseDelay: 1000,
      maxDelay: 30000
    }
  },

  // Content Generation - z.ai coding plan
  llm: {
    provider: 'zai',
    apiKey: process.env.GLM_API_KEY,
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    model: 'glm-4-flash',  // Fast and cost-effective
    maxTokens: 2000
  },

  // Safety
  safety: {
    dryRun: process.env.DRY_RUN !== 'false',
    requireApproval: process.env.REQUIRE_APPROVAL !== 'false',
    approvalTimeoutHours: parseInt(process.env.APPROVAL_TIMEOUT_HOURS) || 24,
    rateLimits: {
      tweet: { max: parseInt(process.env.MAX_TWEETS_PER_DAY) || 10, windowMinutes: 1440 },
      reply: { max: parseInt(process.env.MAX_REPLIES_PER_DAY) || 20, windowMinutes: 1440 },
      like: { max: 50, windowMinutes: 60 },
      apiCall: { max: 100, windowMinutes: 15 }
    }
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: 'data/logs/agent.log'
  },

  // Dashboard web interface
  dashboard: {
    port: parseInt(process.env.DASHBOARD_PORT) || 3456,
    host: process.env.DASHBOARD_HOST || '0.0.0.0',
    auth: {
      enabled: !!(process.env.DASHBOARD_USER && process.env.DASHBOARD_PASSWORD),
      username: process.env.DASHBOARD_USER || '',
      password: process.env.DASHBOARD_PASSWORD || ''
    }
  },

  // Identity (from your setup)
  identity: {
    handle: 'novaisabuilder',
    bio: 'AI agent builder & teacher',
    focus: ['AI agents', 'automation', 'building in public', 'coding']
  },

  // Paths
  paths: {
    state: 'data/state.db',
    content: 'data/content',
    logs: 'data/logs'
  }
};

export default config;
