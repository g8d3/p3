/**
 * EventBus - Simple in-process event emitter for module communication
 * Allows modules to communicate without direct dependencies
 */

import EventEmitter from 'events';
import logger from './logger.js';

const log = logger.module('events');

class EventBus extends EventEmitter {
  constructor() {
    super();
    this.setMaxListeners(50); // Allow many listeners
  }

  /**
   * Emit an event with logging
   * @param {string} event - Event name
   * @param {*} data - Event data
   */
  emit(event, data) {
    log.debug(`Event emitted: ${event}`, data);
    return super.emit(event, data);
  }

  /**
   * Subscribe to an event with error handling
   * @param {string} event - Event name
   * @param {Function} handler - Event handler
   */
  on(event, handler) {
    const wrappedHandler = (data) => {
      try {
        handler(data);
      } catch (error) {
        log.error(`Error in event handler for ${event}: ${error.message}`);
      }
    };
    return super.on(event, wrappedHandler);
  }

  /**
   * Subscribe to an event once
   * @param {string} event - Event name
   * @param {Function} handler - Event handler
   */
  once(event, handler) {
    const wrappedHandler = (data) => {
      try {
        handler(data);
      } catch (error) {
        log.error(`Error in event handler for ${event}: ${error.message}`);
      }
    };
    return super.once(event, wrappedHandler);
  }
}

// Singleton instance
let eventBusInstance = null;

export function getEventBus() {
  if (!eventBusInstance) {
    eventBusInstance = new EventBus();
  }
  return eventBusInstance;
}

export default EventBus;
