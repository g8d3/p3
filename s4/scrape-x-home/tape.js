// Create a fixed div at the top left to display tweet count and short IDs
const countDiv = document.createElement('div');
countDiv.id = 'tweet-count';
countDiv.style.position = 'fixed';
countDiv.style.top = '10px';
countDiv.style.left = '10px';
countDiv.style.background = 'rgba(0, 0, 0, 0.8)';
countDiv.style.color = 'white';
countDiv.style.padding = '5px 10px';
countDiv.style.borderRadius = '5px';
countDiv.style.zIndex = '10000';
countDiv.style.fontSize = '14px';
countDiv.style.fontFamily = 'monospace';
countDiv.style.maxWidth = '80%';
countDiv.style.wordWrap = 'break-word';
document.body.appendChild(countDiv);
// Function to update the count and short tweet IDs
function updateTweetCount() {
  const tweets = document.querySelectorAll('article[data-testid="tweet"]');
  const ids = Array.from(tweets).map(t => {
    const link = t.querySelector('a[href*="/status/"]');
    if (link) {
      const href = link.href;
      const id = href.split('/status/')[1]?.split('/')[0]; // Extract full ID
      return id ? id.slice(-4) : 'none'; // Last 4 digits as short ID
    }
    return 'none';
  });
  countDiv.textContent = `Tweets: ${tweets.length} | IDs: ${ids.join(', ')}`;
}
// Update initially
updateTweetCount();
// Update on scroll
document.addEventListener('scroll', updateTweetCount);
// Also update periodically in case of dynamic loading
setInterval(updateTweetCount, 1000);