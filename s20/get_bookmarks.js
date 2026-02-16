const WebSocket = require('ws');
const http = require('http');

async function requestJSON(url, method = 'GET') {
    return new Promise((resolve, reject) => {
        const req = http.request(url, { method }, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                try {
                    resolve(data ? JSON.parse(data) : {});
                } catch (e) {
                    resolve(data);
                }
            });
        });
        req.on('error', reject);
        req.end();
    });
}

async function getBookmarks() {
    const start = Date.now();
    let targetId = null;

    try {
        // 1. Open chrome://bookmarks in a new tab
        const newPage = await requestJSON('http://localhost:9222/json/new?chrome://bookmarks', 'PUT');
        targetId = newPage.id;
        const wsUrl = newPage.webSocketDebuggerUrl;

        const ws = new WebSocket(wsUrl);

        ws.on('open', () => {
            ws.send(JSON.stringify({ id: 1, method: 'Runtime.enable' }));
        });

        ws.on('message', async (data) => {
            const message = JSON.parse(data);

            if (message.id === 1) {
                // Wait for the bookmarks API to be available
                const expression = `
                    new Promise((resolve) => {
                        const check = () => {
                            if (typeof chrome !== 'undefined' && chrome.bookmarks) {
                                chrome.bookmarks.getTree((tree) => resolve(tree));
                            } else {
                                setTimeout(check, 50);
                            }
                        };
                        check();
                    })
                `;
                ws.send(JSON.stringify({
                    id: 2,
                    method: 'Runtime.evaluate',
                    params: { expression, awaitPromise: true, returnByValue: true }
                }));
            }

            if (message.id === 2) {
                const end = Date.now();
                const bookmarks = message.result.result.value;
                const fs = require('fs');

                // Save to file
                fs.writeFileSync('bookmarks.json', JSON.stringify(bookmarks, null, 2));

                console.log('--- BOOKMARKS RETRIEVED ---');
                console.log(`Success: Successfully retrieved bookmarks in ${end - start}ms.`);
                console.log('Bookmarks saved to: bookmarks.json');

                // Print small summary
                if (bookmarks && bookmarks[0] && bookmarks[0].children) {
                    const bar = bookmarks[0].children.find(c => c.title === "Bookmarks bar");
                    if (bar && bar.children) {
                        console.log(`Found ${bar.children.length} items in the Bookmarks Bar.`);
                    }
                }

                ws.close();

                // 2. Close the tab to leave the browser as it was
                await requestJSON(`http://localhost:9222/json/close/${targetId}`);
            }
        });

        ws.on('error', (err) => {
            console.error('WS Error:', err);
        });

    } catch (error) {
        console.error('Error fetching bookmarks:', error);
    }
}

getBookmarks();
