// opentab.js
async function run() {
    const CDP_HOST = 'http://127.0.0.1:9222';

    try {
        // 1. Validar conexión y ver versión
        const versionRes = await fetch(`${CDP_HOST}/json/version`);
        const versionData = await versionRes.json();
        console.log(`✅ Conectado a: ${versionData.Browser}`);
        console.log(`🎯 Browser WebSocket: ${versionData.webSocketDebuggerUrl}`);

        // 2. Abrir nueva pestaña (Target.createTarget vía HTTP)
        const urlParaAbrir = 'https://example.com';
        const newTabRes = await fetch(`${CDP_HOST}/json/new?${urlParaAbrir}`, { method: 'PUT' });
        const tabData = await newTabRes.json();
        
        console.log(`\n✨ Pestaña abierta!`);
        console.log(`ID: ${tabData.id}`);
        
        // 3. Ver contenido básico (sin entrar en WebSockets complejos)
        // Consultamos la lista de targets para verificar que está activa
        const listRes = await fetch(`${CDP_HOST}/json/list`);
        const list = await listRes.json();
        const myTab = list.find(t => t.id === tabData.id);

        console.log(`\n📝 Estado actual:`);
        console.table({
            Title: myTab.title,
            URL: myTab.url,
            CanInspect: myTab.webSocketDebuggerUrl ? 'YES' : 'NO'
        });

    } catch (e) {
        console.error('❌ Error:', e.message);
        console.log('Asegúrate de que el browser tenga: --remote-debugging-port=9222');
    }
}

run();