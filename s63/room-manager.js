// WebSocket Room Manager — simple channel/room management for ws
// Replaces Socket.IO rooms with a lightweight alternative

export class RoomManager {
  constructor(wss) {
    this.wss = wss;
    // ws._rooms is a Set<string> added to each client
  }

  // Ensure client has _rooms set
  _initClient(ws) {
    if (!ws._rooms) ws._rooms = new Set();
  }

  join(ws, channelId) {
    this._initClient(ws);
    ws._rooms.add(channelId);
  }

  leave(ws, channelId) {
    this._initClient(ws);
    ws._rooms.delete(channelId);
  }

  // Broadcast to all clients in a channel (except sender if skipSelf=true)
  broadcast(channelId, message, skipWs = null) {
    if (!this.wss) return;
    const data = typeof message === 'string' ? message : JSON.stringify(message);
    this.wss.clients.forEach(client => {
      if (client.readyState === 1 && client._rooms?.has(channelId) && client !== skipWs) {
        client.send(data);
      }
    });
  }

  // Broadcast to ALL connected clients
  broadcastAll(message) {
    if (!this.wss) return;
    const data = typeof message === 'string' ? message : JSON.stringify(message);
    this.wss.clients.forEach(client => {
      if (client.readyState === 1) client.send(data);
    });
  }

  // Broadcast to a specific room:subscribers (for errors/tasks)
  broadcastTo(room, message) {
    this.broadcast(room, message);
  }

  // Get count of clients in a room
  count(channelId) {
    let count = 0;
    this.wss?.clients.forEach(client => {
      if (client._rooms?.has(channelId)) count++;
    });
    return count;
  }
}
