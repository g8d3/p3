const WebSocket = require('ws');

const CDP_PORT = 9222;
const DOWNLOAD_DIR = '/home/vuos/Downloads';

async function run() {
  // Connect to browser via CDP WebSocket
  const ws = new WebSocket(`ws://localhost:${CDP_PORT}/devtools/page`);
  
  await new Promise(resolve => ws.on('open', resolve));
  
  // Get available targets
  const res = await fetch(`http://localhost:${CDP_PORT}/json`);
  const targets = await res.json();
  const pageTarget = targets.find(t => t.type === 'page');
  
  if (!pageTarget) {
    console.error('No page target found');
    process.exit(1);
  }
  
  // Connect to specific page
  const pageWs = new WebSocket(pageTarget.webSocketDebuggerUrl);
  await new Promise(resolve => pageWs.on('open', resolve));
  
  let messageId = 0;
  function send(method, params = {}) {
    return new Promise(resolve => {
      const id = ++messageId;
      const handler = (data) => {
        const msg = JSON.parse(data);
        if (msg.id === id) {
          pageWs.removeListener('message', handler);
          resolve(msg.result);
        }
      };
      pageWs.on('message', handler);
      pageWs.send(JSON.stringify({ id, method, params }));
    });
  }
  
  // Enable required domains
  await send('Page.enable');
  await send('Runtime.enable');
  await send('DOM.enable');
  
  // Set download behavior
  await send('Page.setDownloadBehavior', {
    behavior: 'allow',
    downloadPath: DOWNLOAD_DIR
  });
  
  console.log('Navigating to pixabay...');
  await send('Page.navigate', { url: 'https://pixabay.com/sound-effects/' });
  
  // Wait for load
  await new Promise(resolve => setTimeout(resolve, 3000));
  
  // Find and click download button
  console.log('Finding download button...');
  const { root } = await send('DOM.getDocument');
  const { nodeId } = await send('DOM.querySelector', {
    nodeId: root.nodeId,
    selector: 'button[aria-label*="Download"], button[class*="download"]'
  });
  
  if (!nodeId) {
    console.log('Trying alternative selector...');
    const { nodeId: altNode } = await send('DOM.querySelector', {
      nodeId: root.nodeId,
      selector: 'button'
    });
  }
  
  // Get all buttons and find download
  const { nodeIds } = await send('DOM.querySelectorAll', {
    nodeId: root.nodeId,
    selector: 'button'
  });
  
  let downloadBtnId = null;
  for (const id of nodeIds) {
    const { value } = await send('DOM.getAttributes', { nodeId: id });
    const { text } = await send('DOM.getNodeText', { nodeId: id }).catch(() => ({ text: '' }));
    if (text.toLowerCase().includes('download')) {
      downloadBtnId = id;
      console.log('Found download button:', text);
      break;
    }
  }
  
  if (!downloadBtnId) {
    console.log('No download button found, using first button');
    downloadBtnId = nodeIds[0];
  }
  
  // Scroll into view and click
  await send('DOM.scrollIntoViewIfNeeded', { nodeId: downloadBtnId });
  await send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: 100,
    y: 100,
    button: 'left'
  });
  await send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: 100,
    y: 100,
    button: 'left'
  });
  
  console.log('Clicked download button');
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  // Check for new files
  const { exec } = require('child_process');
  exec(`ls -lt ${DOWNLOAD_DIR} | head -5`, (err, stdout) => {
    console.log('Recent files in Downloads:');
    console.log(stdout);
  });
  
  pageWs.close();
  ws.close();
}

run().catch(console.error);
