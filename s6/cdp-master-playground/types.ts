
export interface BrowserConnection {
  id: string;
  name: string;
  url: string;
  status: 'connecting' | 'connected' | 'error' | 'disconnected';
  error?: string;
  isMock?: boolean;
}

export interface Target {
  id: string;
  browserId: string; // Link to the connection
  name: string;
  url: string;
  status: 'connected' | 'disconnected';
  type: string;
}

export interface CDPCommand {
  domain: string;
  method: string;
  description: string;
  parameters: CDPParameter[];
  returns?: CDPParameter[];
}

export interface CDPParameter {
  name: string;
  type: string;
  optional: boolean;
  description: string;
}

export interface LogEntry {
  id: string;
  timestamp: number;
  direction: 'sent' | 'received' | 'event' | 'error' | 'test';
  browserId: string;
  targetId?: string;
  method: string;
  payload: any;
}

export interface DomainGroup {
  name: string;
  commands: CDPCommand[];
}

export interface TestStep {
  name: string;
  status: 'pending' | 'running' | 'passed' | 'failed';
  message?: string;
}
