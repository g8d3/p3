import { ChannelStore } from './channels.js';

export class StreamRelay {
  constructor(roomManager) {
    this.roomManager = roomManager;
    this.channels = new ChannelStore();
  }

  createChannel(id, name, agentType) {
    return this.channels.create(id, name, agentType);
  }

  broadcastFrame(channelId, frameBuffer) {
    const channel = this.channels.get(channelId);
    if (!channel) return;

    const base64 = frameBuffer.toString('base64');
    this.channels.setFrame(channelId, base64);

    this.roomManager.broadcast(`channel:${channelId}`, {
      type: 'stream:frame',
      channelId,
      frame: base64,
      timestamp: Date.now(),
      frameCount: channel.frameCount,
    });
  }

  broadcastStatus(channelId, status, text) {
    this.channels.setStatus(channelId, status);
    this.roomManager.broadcast(`channel:${channelId}`, {
      type: 'agent:status',
      channelId,
      status,
      text,
    });
  }

  getChannels() {
    return this.channels.getAll().map(ch => ({
      id: ch.id,
      name: ch.name,
      agentType: ch.agentType,
      viewers: ch.viewers,
      status: ch.status,
      startedAt: ch.startedAt,
      frameCount: ch.frameCount,
      hasPreview: !!ch.lastFrame,
    }));
  }

  removeChannel(channelId) {
    this.channels.remove(channelId);
    this.roomManager.broadcast(`channel:${channelId}`, {
      type: 'stream:ended',
      channelId,
    });
  }
}
