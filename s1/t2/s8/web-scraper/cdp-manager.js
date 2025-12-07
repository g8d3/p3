const CDP = require('chrome-remote-interface');

class CDPManager {
  constructor(port = 9222) {
    this.port = port;
    this.client = null;
  }

  async connect() {
    try {
      this.client = await CDP({ port: this.port });
      console.log('Connected to CDP');
    } catch (error) {
      throw new Error(`Failed to connect to CDP on port ${this.port}: ${error.message}`);
    }
  }

  async disconnect() {
    if (this.client) {
      await this.client.close();
      this.client = null;
      console.log('Disconnected from CDP');
    }
  }

  async listTargets() {
    if (!this.client) throw new Error('Not connected to CDP');

    const { Target } = this.client;
    const targets = await Target.getTargets();
    return targets.targetInfos
      .filter(target => target.type === 'page')
      .map(target => ({
        id: target.targetId,
        title: target.title,
        url: target.url
      }));
  }

  async navigateTo(targetId, url) {
    if (!this.client) throw new Error('Not connected to CDP');

    const { Target } = this.client;
    await Target.activateTarget({ targetId });

    // Get the session for the target
    const targetClient = await CDP({ target: targetId, port: this.port });
    const { Page, Runtime } = targetClient;

    await Page.enable();
    await Page.navigate({ url });
    await Page.loadEventFired();

    return targetClient;
  }

  async getHTML(targetId) {
    if (!this.client) throw new Error('Not connected to CDP');

    const targetClient = await CDP({ target: targetId, port: this.port });
    const { Runtime } = targetClient;

    const result = await Runtime.evaluate({
      expression: 'document.documentElement.outerHTML'
    });

    await targetClient.close();
    return result.result.value;
  }

  async getAccessibilitySnapshot(targetId) {
    if (!this.client) throw new Error('Not connected to CDP');

    const targetClient = await CDP({ target: targetId, port: this.port });
    const { Accessibility } = targetClient;

    await Accessibility.enable();
    const axTree = await Accessibility.getFullAXTree();

    await targetClient.close();
    return axTree.nodes;
  }
}

module.exports = CDPManager;