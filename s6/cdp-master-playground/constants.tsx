
import { DomainGroup } from './types';

export const CDP_DOMAINS: DomainGroup[] = [
  {
    name: 'Target',
    commands: [
      {
        domain: 'Target',
        method: 'createTarget',
        description: 'Creates a new page.',
        parameters: [
          { name: 'url', type: 'string', optional: false, description: 'The initial URL the page will be navigated to.' },
          { name: 'width', type: 'integer', optional: true, description: 'Frame width in DIP (visible only in headless mode).' },
          { name: 'height', type: 'integer', optional: true, description: 'Frame height in DIP (visible only in headless mode).' },
          { name: 'browserContextId', type: 'string', optional: true, description: 'The browser context to create the page in.' },
          { name: 'enableBeginFrameControl', type: 'boolean', optional: true, description: 'Whether BeginFrames for this target will be controlled via DevTools.' },
          { name: 'newWindow', type: 'boolean', optional: true, description: 'Whether to create a new window or tab (default is false, tab).' },
          { name: 'background', type: 'boolean', optional: true, description: 'Whether to create the target in background or foreground (default is false, foreground).' }
        ]
      },
      {
        domain: 'Target',
        method: 'closeTarget',
        description: 'Closes the target. If the target is a page that gets closed too.',
        parameters: [
          { name: 'targetId', type: 'string', optional: false, description: 'Target identifier.' }
        ]
      },
      {
        domain: 'Target',
        method: 'getTargetInfo',
        description: 'Returns information about a target.',
        parameters: [
          { name: 'targetId', type: 'string', optional: true, description: 'Target identifier.' }
        ]
      }
    ]
  },
  {
    name: 'Browser',
    commands: [
      {
        domain: 'Browser',
        method: 'getVersion',
        description: 'Returns version information.',
        parameters: []
      },
      {
        domain: 'Browser',
        method: 'getHistograms',
        description: 'Returns histograms.',
        parameters: [
          { name: 'query', type: 'string', optional: true, description: 'Sub-string to filter descriptor names by.' },
          { name: 'delta', type: 'boolean', optional: true, description: 'If true, retrieve delta since last call.' }
        ]
      }
    ]
  },
  {
    name: 'Page',
    commands: [
      {
        domain: 'Page',
        method: 'navigate',
        description: 'Navigates current page to the given URL.',
        parameters: [
          { name: 'url', type: 'string', optional: false, description: 'URL to navigate the page to.' },
          { name: 'referrer', type: 'string', optional: true, description: 'Referrer URL.' }
        ]
      },
      {
        domain: 'Page',
        method: 'reload',
        description: 'Reloads given page optionally ignoring the cache.',
        parameters: [
          { name: 'ignoreCache', type: 'boolean', optional: true, description: 'If true, browser cache is ignored.' }
        ]
      },
      {
        domain: 'Page',
        method: 'captureScreenshot',
        description: 'Capture page screenshot.',
        parameters: [
          { name: 'format', type: 'string', optional: true, description: 'Image format (jpeg or png).' },
          { name: 'quality', type: 'integer', optional: true, description: 'Compression quality from 0 to 100.' }
        ]
      }
    ]
  },
  {
    name: 'Runtime',
    commands: [
      {
        domain: 'Runtime',
        method: 'evaluate',
        description: 'Evaluates expression on global object.',
        parameters: [
          { name: 'expression', type: 'string', optional: false, description: 'Expression to evaluate.' },
          { name: 'returnByValue', type: 'boolean', optional: true, description: 'Whether the result is expected to be a JSON object.' }
        ]
      }
    ]
  },
  {
    name: 'Network',
    commands: [
      {
        domain: 'Network',
        method: 'enable',
        description: 'Enables network tracking, network events will now be delivered to the client.',
        parameters: []
      },
      {
        domain: 'Network',
        method: 'setExtraHTTPHeaders',
        description: 'Specifies whether to always send extra HTTP headers with the requests from this page.',
        parameters: [
          { name: 'headers', type: 'object', optional: false, description: 'Map with extra HTTP headers.' }
        ]
      }
    ]
  },
  {
    name: 'Emulation',
    commands: [
      {
        domain: 'Emulation',
        method: 'setDeviceMetricsOverride',
        description: 'Overrides the values of device screen dimensions.',
        parameters: [
          { name: 'width', type: 'integer', optional: false, description: 'Overriding width value in pixels.' },
          { name: 'height', type: 'integer', optional: false, description: 'Overriding height value in pixels.' },
          { name: 'deviceScaleFactor', type: 'number', optional: false, description: 'Overriding device scale factor value.' },
          { name: 'mobile', type: 'boolean', optional: false, description: 'Whether to emulate mobile device.' }
        ]
      }
    ]
  }
];
