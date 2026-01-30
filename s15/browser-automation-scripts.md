# Browser Automation Scripts for Copy Trading Research

## Overview
This file documents repetitive browser actions identified during research and provides automation scripts to streamline the workflow.

## Repetitive Browser Actions Identified

### 1. Google Search Actions
**Pattern**: Navigate to Google, search for specific queries, navigate through results

**Actions**:
- Navigate to google.com
- Click on search box
- Type search query
- Press Enter to search
- Navigate through search results pages
- Click on relevant links

**Frequency**: High (5-10 times per research session)

### 2. Page Navigation Actions
**Pattern**: Navigate to URLs, scroll through content, find specific sections

**Actions**:
- Navigate to URL
- Scroll to specific positions
- Use evaluate() to extract page data
- Find specific text sections using includes() or regex

**Frequency**: High (every page visited)

### 3. Link Clicking Actions
**Pattern**: Click on search results or page links to access content

**Actions**:
- Click on search result links
- Click on navigation menu items
- Click on "Read more" links
- Click on internal page links

**Frequency**: Very High (20-30 times per research session)

### 4. Data Extraction Actions
**Pattern**: Extract specific data points, statistics, or metrics from pages

**Actions**:
- Use page.evaluate() to execute JavaScript
- Extract text content
- Find and collect metrics (PnL, ROI, win rates, etc.)
- Parse tables and structured data

**Frequency**: Medium (every research page)

## Automation Scripts

### Script 1: Automated Google Search and Navigate
**Purpose**: Automate initial search and navigation to relevant pages

```javascript
// search-google.js
async function searchAndNavigate(searchQuery, targetUrl = null) {
  // Navigate to Google
  await page.goto('https://www.google.com');
  
  // Find and click search box
  const searchBox = await page.locator('input[type="search"]');
  if (searchBox) {
    await searchBox.click();
    await searchBox.fill(searchQuery);
    await searchBox.press('Enter');
    
    // Wait for results to load
    await page.waitForTimeout(3000);
    
    // If target URL provided, navigate to it
    if (targetUrl) {
      await page.goto(targetUrl);
    }
  }
}

// Usage: searchAndNavigate('"GMX copy trading" "GLP vault" "synthetix" perp DEX');
```

### Script 2: Automated Page Content Extraction
**Purpose**: Extract key information, metrics, and data from research pages

```javascript
// extract-content.js
async function extractPageContent() {
  // Get page text content
  const pageText = await page.evaluate(() => {
    return document.body.innerText;
  });
  
  // Find specific sections
  const copyTradingSections = await page.evaluate(() => {
    const text = document.body.innerText;
    const lines = text.split('\n');
    const sections = [];
    
    lines.forEach((line, index) => {
      if (line.toLowerCase().includes('copy trading') || 
          line.toLowerCase().includes('vault') || 
          line.toLowerCase().includes('sharpe') ||
          line.toLowerCase().includes('roi') ||
          line.toLowerCase().includes('win rate') ||
          line.toLowerCase().includes('pnl') ||
          line.toLowerCase().includes('maximum drawdown')) {
        sections.push({
          index: index,
          text: line.trim().substring(0, 300)
        });
      }
    });
    
    return sections.slice(0, 50);
  });
  
  return copyTradingSections;
}

// Usage: await extractPageContent();
```

### Script 3: Platform Comparison Matrix Generator
**Purpose**: Generate structured comparison data for copy trading platforms

```javascript
// generate-comparison.js
async function generatePlatformComparison(platforms) {
  const comparisonData = {
    timestamp: new Date().toISOString(),
    platforms: platforms.map(platform => ({
      name: platform.name,
      copyTradingFeature: platform.copyTradingFeature,
      feeStructure: platform.feeStructure,
      riskManagement: platform.riskManagement,
      accessibility: platform.accessibility,
      status: platform.status
    }))
  };
  
  // Write to CSV file
  const fs = require('fs');
  const csv = platforms.map(p => 
    `${p.name},${p.copyTradingFeature},${p.feeStructure},${p.riskManagement},${p.accessibility},${p.status}`
  ).join('\n');
  
  await fs.promises.writeFile('platform-comparison.csv', csv);
  return comparisonData;
}

// Example platforms data
const examplePlatforms = [
  {
    name: 'Hyperliquid',
    copyTradingFeature: 'User Vaults - On-chain copy trading, 10% profit share to leader',
    feeStructure: '0% for makers, taker fees only',
    riskManagement: 'Withdrawal lock-up (72h), HLP vault with PnL tracking',
    accessibility: 'High - Public vault data available, no login required for viewing',
    status: 'Active'
  },
  {
    name: 'Simpfor.fun',
    copyTradingFeature: 'Multi-platform copy trading - Copy top traders from Aster, GMX, dYdX',
    feeStructure: 'Platform fees, varies by platform',
    riskManagement: 'Managed vaults, leader compensation structure',
    accessibility: 'Medium - Requires login for access, public rankings available',
    status: 'Active'
  },
  {
    name: 'dYdX',
    copyTradingFeature: 'Single-name Vaults - Automated market-making, not direct copy trading',
    feeStructure: 'Maker fees, revenue share to vault operators',
    riskManagement: 'Permissionless deposits, protocol-native risk management',
    accessibility: 'Medium - Public vault data available, requires technical understanding',
    status: 'Active (v4)'
  }
];

// Usage: await generatePlatformComparison(examplePlatforms);
```

### Script 4: Trader Metrics Analyzer
**Purpose**: Analyze trader performance data to distinguish skill from luck

```javascript
// analyze-trader.js
async function analyzeTraderMetrics(traderData) {
  const metrics = {
    // Risk-adjusted metrics
    sharpeRatio: calculateSharpeRatio(traderData.returns),
    sortinoRatio: calculateSortinoRatio(traderData.returns),
    maxDrawdown: calculateMaxDrawdown(traderData.accountHistory),
    valueAtRisk: calculateVaR(traderData.returns, traderData.riskLevel),
    
    // Win rate analysis
    winRate: traderData.profitableTrades / traderData.totalTrades,
    rollingWinRate: calculateRollingWinRate(traderData.tradeHistory, 30),
    
    // Consistency metrics
    monthlyROI: calculateMonthlyROI(traderData.monthlyReturns),
    rollingStdDev: calculateStdDeviation(traderData.returns, 90),
    correlationWithMarket: calculateCorrelation(traderData.returns, marketReturns),
    
    // Significance testing
    tTestValue: performTTest(traderData.returns),
    zScore: (traderData.averageReturn - traderData.riskFreeRate) / traderData.returnStdDev
  };
  
  return metrics;
}

function calculateSharpeRatio(returns) {
  // Risk-adjusted return metric
  // Higher = better risk-adjusted performance
  // Implementation would require historical return data
  return null; // Placeholder
}

function calculateMaxDrawdown(accountHistory) {
  // Largest peak-to-trough decline
  // Lower = better risk management
  let maxDrawdown = 0;
  let peak = 0;
  
  accountHistory.forEach(balance => {
    if (balance > peak) {
      peak = balance;
    } else {
      const drawdown = ((peak - balance) / peak) * 100;
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
      }
    }
  });
  
  return maxDrawdown;
}

function calculateMonthlyROI(monthlyReturns) {
  // Sustainable performance metric
  // Average return percentage over time
  const avgROI = monthlyReturns.reduce((sum, r) => sum + r, 0) / monthlyReturns.length;
  return avgROI;
}

function calculateStdDeviation(returns, days) {
  // Measures consistency/volatility
  // Lower = more consistent, predictable
  // Higher = more volatile, unpredictable
  let sum = 0;
  let sumSq = 0;
  
  returns.slice(-days).forEach(r => {
    sum += r;
    sumSq += r * r;
  });
  
  const mean = sum / returns.length;
  const variance = sumSq / returns.length - (mean * mean);
  return Math.sqrt(variance);
}
```

## Scheduling Manual

### Using cron (Linux/macOS)
To automate running these scripts at regular intervals:

```bash
# Add to crontab
crontab -e 0 2 * * * * * * bash ~/code/p3/s15/run-research-update.sh

# Create update script
cat > ~/code/p3/s15/run-research-update.sh << 'EOF'
#!/bin/bash
cd ~/code/p3/s15
node search-google.js "copy trading perp DEX 2026" >> research-log.txt
node extract-content.js >> research-log.txt
EOF

# Make executable
chmod +x ~/code/p3/s15/run-research-update.sh
```

### Using Windows Task Scheduler
To automate on Windows:

```powershell
# Create scheduled task
$action = New-ScheduledTask
$trigger = New-ScheduledTaskTrigger -Once -At "02:00 AM"
$action = New-ScheduledTaskTrigger -Daily -At "09:00 AM"

$script = "C:\Users\username\code\p3\s15\run-research-update.cmd"
$task = New-ScheduledTask -Action "Execute" -Argument "C:\Users\username\code\p3\s15\run-research-update.cmd"

Register-ScheduledTask -Task $task -Trigger $trigger
```

### Using Node.js Scheduler
For more flexible scheduling within Node.js applications:

```javascript
// schedule-research.js
const schedule = require('node-schedule');
const job = schedule.scheduleJob('0 0 * * * *', () => {
  console.log('Running automated copy trading research update...');
  
  // Execute research scripts
  exec('node ~/code/p3/s15/search-google.js', (error, stdout, stderr) => {
    if (error) {
      console.error('Search failed:', error);
    }
  });
});
```

## Implementation Notes

### Prerequisites
1. Node.js installed (for JavaScript automation)
2. Playwright installed (for browser automation)
3. Python environment (optional, for data analysis)

### Running the Scripts

```bash
# Navigate to directory
cd ~/code/p3/s15

# Run automated search
node search-google.js '"best copy trading platforms 2026"'

# Extract content from multiple URLs
node extract-content.js --url="https://hyperliquid.com" >> hyperliquid-data.txt
node extract-content.js --url="https://simpfor.fun" >> simpfor-data.txt
```

### Data File Formats

#### CSV for Platform Comparison (copy-trading-platforms.csv)
```csv
Platform,Copy Trading Feature,Fee Structure,Risk Management,Accessibility,Status
Hyperliquid,User Vaults - 10% leader profit share,0% maker fees,Withdrawal lock-up,High - Public data,Active
Simpfor.fun,Multi-platform copy trading,Platform fees,Managed vaults,Medium - Requires login,Active
dYdX,Single-name Vaults - Automated market-making,Maker fees,Permissionless deposits,Medium - Public vault data,Active (v4)
```

#### JSON for Detailed Metrics (trader-metrics.json)
```json
{
  "last_updated": "2026-01-29",
  "platforms": [
    {
      "name": "Hyperliquid",
      "traders_analyzed": [],
      "best_performers": [],
      "key_features": ["User Vaults", "10% profit share", "Public performance data"]
    },
    {
      "name": "Simpfor.fun",
      "traders_analyzed": [],
      "best_performers": [],
      "key_features": ["Multi-platform support", "Top trader rankings", "API access"]
    },
    {
      "name": "dYdX",
      "traders_analyzed": [],
      "best_performers": [],
      "key_features": ["Automated market-making", "Fair price index", "Protocol integration"]
    }
  ]
}
```

## Customization

### Adding New Platforms
To add a new platform to the automation workflow:

1. Add platform details to `platform-data.json`
2. Run content extraction script on platform URL
3. Update comparison matrix
4. Generate trader analysis if public data available

### Troubleshooting

**Browser Not Starting**: Ensure Playwright server is running
- `npx playwright install`
- `npx playwright install chromium`

**Script Errors**: Check console output for JavaScript errors
**Page Timeouts**: Increase wait times if pages load slowly
- `await page.waitForTimeout(5000)` instead of default 3000ms

**Rate Limiting**: Add delays between actions to avoid being blocked
- `await page.waitForTimeout(2000)`
