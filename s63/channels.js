// In-memory channel state store
export class ChannelStore {
  constructor() {
    this.channels = new Map();
  }

  create(id, name, agentType) {
    const channel = {
      id,
      name,
      agentType,
      viewers: 0,
      status: 'starting',
      startedAt: Date.now(),
      lastFrame: null,
      frameCount: 0,
      ended: false,
    };
    this.channels.set(id, channel);
    return channel;
  }

  get(id) {
    return this.channels.get(id);
  }

  getAll() {
    return Array.from(this.channels.values()).filter(c => !c.ended);
  }

  remove(id) {
    const ch = this.channels.get(id);
    if (ch) {
      ch.ended = true;
      ch.status = 'ended';
    }
  }

  setStatus(id, status) {
    const ch = this.channels.get(id);
    if (ch) ch.status = status;
  }

  setFrame(id, frameBase64) {
    const ch = this.channels.get(id);
    if (ch) {
      ch.lastFrame = frameBase64;
      ch.frameCount++;
      ch.lastFrameTime = Date.now();
    }
  }
}
