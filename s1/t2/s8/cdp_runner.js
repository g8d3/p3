const CDP = require('chrome-remote-interface');
const readline = require('readline');

async function run() {
  try {
    const client = await CDP({ port: 9222 });
    const { Runtime, Target } = client;
    const context = { client, Runtime, Target };

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      completer: (line) => {
        const parts = line.split('.');
        let obj = context;
        const prefix = parts[parts.length - 1];
        for (let i = 0; i < parts.length - 1; i++) {
          const part = parts[i];
          if (obj && typeof obj === 'object' && part in obj) {
            obj = obj[part];
          } else {
            return [[], line];
          }
        }
        if (obj && typeof obj === 'object') {
          const keys = Object.getOwnPropertyNames(obj).filter(k => k.startsWith(prefix));
          return [keys, prefix];
        }
        return [[], line];
      }
    });

    function ask() {
      rl.question('> ', async (code) => {
        if (code.trim() === 'exit') {
          client.close();
          rl.close();
          return;
        }
        try {
          const func = eval(`(async (client, Runtime, Target) => { return (${code}); })`);
          const result = await func(client, Runtime, Target);
          if (result !== undefined) console.log(result);
        } catch (err) {
          console.error('Error:', err);
        }
        ask();
      });
    }

    ask();
  } catch (err) {
    console.error('Error:', err);
  }
}

run();