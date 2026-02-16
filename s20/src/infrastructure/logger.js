import fs from 'fs';
import path from 'path';
import { config } from '../../config/defaults.js';

const LOG_LEVELS = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3
};

class Logger {
  constructor(moduleName = 'app') {
    this.moduleName = moduleName;
    this.level = config.logging.level || 'info';
    this.logFile = config.logging.file || 'data/logs/agent.log';
    this._ensureLogDirectory();
  }

  _ensureLogDirectory() {
    const logDir = path.dirname(this.logFile);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
  }

  _shouldLog(level) {
    const currentLevel = LOG_LEVELS[this.level] ?? LOG_LEVELS.info;
    const messageLevel = LOG_LEVELS[level] ?? LOG_LEVELS.info;
    return messageLevel >= currentLevel;
  }

  _formatMessage(level, message, meta = {}) {
    const timestamp = new Date().toISOString();
    const levelUpper = level.toUpperCase().padEnd(5);
    const metaStr = Object.keys(meta).length > 0 ? ` ${JSON.stringify(meta)}` : '';
    return `[${timestamp}] [${levelUpper}] [${this.moduleName}] ${message}${metaStr}`;
  }

  _write(level, message, meta = {}) {
    if (!this._shouldLog(level)) return;

    const formattedMessage = this._formatMessage(level, message, meta);

    // Console output
    console.log(formattedMessage);

    // File output
    try {
      fs.appendFileSync(this.logFile, formattedMessage + '\n', 'utf8');
    } catch (err) {
      console.error(`Failed to write to log file: ${err.message}`);
    }
  }

  debug(message, meta = {}) {
    this._write('debug', message, meta);
  }

  info(message, meta = {}) {
    this._write('info', message, meta);
  }

  warn(message, meta = {}) {
    this._write('warn', message, meta);
  }

  error(message, meta = {}) {
    this._write('error', message, meta);
  }

  module(moduleName) {
    const childLogger = new Logger(moduleName);
    childLogger.level = this.level;
    childLogger.logFile = this.logFile;
    return childLogger;
  }
}

// Export default logger instance
const logger = new Logger();

export default logger;
export { Logger };
