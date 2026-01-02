const { chromium } = require('playwright');
const fs = require('fs');
const readline = require('readline');

async function scrapeGitHubTopics(url, start = 0, limit = 100, headless = false, cdpUrl = 'http://localhost:9222') {
  console.log('Connecting to browser...');
  let browser;
  if (headless) {
    browser = await chromium.launch({ headless: true });
  } else {
    browser = await chromium.connectOverCDP(cdpUrl);
  }

  console.log('Getting existing pages...');
  const contexts = browser.contexts();
  console.log(`Found ${contexts.length} contexts.`);
  for (let i = 0; i < contexts.length; i++) {
    const pages = contexts[i].pages();
    console.log(`Context ${i} has ${pages.length} pages:`);
    for (let j = 0; j < pages.length; j++) {
      try {
        const title = await pages[j].title();
        const url = pages[j].url();
        console.log(`  Page ${j}: Title: "${title}", URL: "${url}"`);
      } catch (e) {
        console.log(`  Page ${j}: Error getting title/URL`);
      }
    }
  }
  // Create a new tab in the existing browser window
  let page;
  if (contexts.length > 0) {
    page = await contexts[0].newPage();
    console.log('Created new page in existing context.');
  } else {
    page = await browser.newPage();
    console.log('No contexts, created new page.');
  }

  console.log('Navigating to URL...');
  // Navigate to the URL
  await page.goto(url);
  console.log('Waiting for page load...');
  await page.waitForLoadState('networkidle');
  console.log('Page loaded.');

  let repos = [];
  let hasMore = true;

  while (hasMore && repos.length < start + limit) {
    console.log(`Scraping repos... Current count: ${repos.length}`);
    // Scrape current repositories
    const currentRepos = await page.$$eval('article', articles => {
      return articles.map(article => {
        const nameLink = article.querySelector('h3 a');
        const owner = nameLink ? nameLink.href.split('/').slice(-1)[0] : '';
        const repo = nameLink ? nameLink.textContent.trim() : '';
        const fullName = `${owner}/${repo}`;
        const repoUrl = nameLink ? `${nameLink.href}/${repo}` : '';
        const userUrl = `https://github.com/${owner}`;

        const description = article.querySelector('p.color-fg-muted.mb-0') ? article.querySelector('p.color-fg-muted.mb-0').textContent.trim() : '';

        const starsElement = article.querySelector('#repo-stars-counter-star');
        const stars = starsElement ? starsElement.textContent.trim() : '';

        const language = article.querySelector('[itemprop="programmingLanguage"]') ? article.querySelector('[itemprop="programmingLanguage"]').textContent.trim() : '';

        const updatedElement = article.querySelector('relative-time');
        const updated = updatedElement ? updatedElement.getAttribute('title') : '';

        const labels = Array.from(article.querySelectorAll('a.topic-tag-link')).map(a => ({
          text: a.textContent.trim(),
          url: a.href
        }));

        return {
          fullName,
          owner,
          repo,
          description,
          stars,
          language,
          updated,
          repoUrl,
          userUrl,
          labels
        };
      });
    });

    console.log(`Found ${currentRepos.length} articles on page.`);
    // Add new repos, avoiding duplicates and respecting limit
    const remaining = start + limit - repos.length;
    let added = 0;
    for (const repo of currentRepos) {
      if (added >= remaining) break;
      if (!repos.find(r => r.fullName === repo.fullName)) {
        repos.push(repo);
        added++;
      }
    }
    console.log(`Added ${added} new repos. Total: ${repos.length}`);

    // Check for "Load more" button
    const loadMoreButton = await page.$('button.ajax-pagination-btn');
    if (loadMoreButton && repos.length < start + limit) {
      console.log('Clicking "Load more"...');
      await loadMoreButton.click();
      console.log('Waiting for new content...');
      await page.waitForTimeout(2000); // Wait for new content to load
    } else {
      hasMore = false;
      console.log('No more to load or max reached.');
    }
  }

  // Bring page to front and take screenshot
  await page.bringToFront();
  await page.screenshot({ path: 'debug.png' });
  console.log('Page title:', await page.title());

  await browser.close();
  return repos.slice(start, start + limit);
}

async function main() {
  const url = 'https://github.com/topics/low-code';
  let start = 0;
  let limit = 5; // Configurable N
  let headless = false;
  let cdpUrl = process.env.CDP_URL || 'http://localhost:9222';

  if (process.argv[2]) {
    if (!isNaN(process.argv[2])) {
      start = parseInt(process.argv[2]);
      if (process.argv[3] && !isNaN(process.argv[3])) {
        limit = parseInt(process.argv[3]);
        if (process.argv[4]) {
          if (process.argv[4] === 'headless') {
            headless = true;
            if (process.argv[5]) cdpUrl = process.argv[5];
          } else if (process.argv[4].startsWith('http')) {
            cdpUrl = process.argv[4];
          }
        }
      } else {
        // argv[3] not a number, check if headless or http
        if (process.argv[3] === 'headless') {
          headless = true;
          if (process.argv[4]) cdpUrl = process.argv[4];
        } else if (process.argv[3] && process.argv[3].startsWith('http')) {
          cdpUrl = process.argv[3];
        }
      }
    } else if (process.argv[2] === 'headless') {
      headless = true;
      if (process.argv[3]) cdpUrl = process.argv[3];
    } else if (process.argv[2].startsWith('http')) {
      cdpUrl = process.argv[2];
    } else {
      console.log('Usage: node scrape.js [start] [limit] [headless] [cdpUrl]');
      process.exit(1);
    }
  }

  try {
    const data = await scrapeGitHubTopics(url, start, limit, headless, cdpUrl);

    // Generate CSV
    const csvHeader = 'Full Name,Owner,Repo,Description,Stars,Language,Updated,Repo URL,User URL,Labels\n';
    const csvRows = data.map(repo => {
      const description = repo.description.replace(/"/g, '""');
      const labelsStr = JSON.stringify(repo.labels).replace(/"/g, '""');
      return `"${repo.fullName}","${repo.owner}","${repo.repo}","${description}","${repo.stars}","${repo.language}","${repo.updated}","${repo.repoUrl}","${repo.userUrl}","${labelsStr}"`;
    }).join('\n');
    const csvContent = csvHeader + csvRows + '\n';

    if (fs.existsSync('repos.csv')) {
      // Append without header
      fs.appendFileSync('repos.csv', csvRows + '\n');
      console.log('CSV appended to repos.csv');
    } else {
      // Write with header
      fs.writeFileSync('repos.csv', csvContent);
      console.log('CSV saved to repos.csv');
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

main();