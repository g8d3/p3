"""
AutoContent - Logging Module
Provides structured logging with error tracking
"""

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ErrorLog:
    """Error log entry"""
    timestamp: str
    component: str
    error_type: str
    message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_method: Optional[str] = None


class AutoContentLogger:
    """Centralized logging with error tracking"""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Main logger
        self.logger = logging.getLogger("AutoContent")
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler
        file_handler = logging.FileHandler(
            self.logs_dir / f"autocontent_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        # Error tracking
        self.errors: list[ErrorLog] = []
        self._load_errors()
    
    def _load_errors(self):
        """Load existing errors from file"""
        error_file = self.logs_dir / "errors.json"
        if error_file.exists():
            try:
                with open(error_file) as f:
                    self.errors = [ErrorLog(**e) for e in json.load(f)]
            except:
                self.errors = []
    
    def _save_errors(self):
        """Save errors to file"""
        error_file = self.logs_dir / "errors.json"
        with open(error_file, "w") as f:
            json.dump([vars(e) for e in self.errors], f, indent=2)
    
    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, extra=kwargs)
    
    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra=kwargs)
    
    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, extra=kwargs)
    
    def error(self, msg: str, component: str = "unknown", 
              stack_trace: Optional[str] = None, **kwargs):
        self.logger.error(msg, extra=kwargs)
        
        # Log error
        error_log = ErrorLog(
            timestamp=datetime.now().isoformat(),
            component=component,
            error_type=type(msg).__name__,
            message=str(msg),
            stack_trace=stack_trace,
            context=kwargs
        )
        self.errors.append(error_log)
        self._save_errors()
    
    def critical(self, msg: str, component: str = "unknown", **kwargs):
        self.logger.critical(msg, extra=kwargs)
        self.error(msg, component=component, **kwargs)
    
    def get_unresolved_errors(self) -> list[ErrorLog]:
        """Get all unresolved errors"""
        return [e for e in self.errors if not e.resolved]
    
    def mark_resolved(self, error: ErrorLog, method: str):
        """Mark an error as resolved"""
        error.resolved = True
        error.resolution_method = method
        self._save_errors()
        self.info(f"Resolved error: {error.message} via {method}")
    
    def log_operation(self, operation: str, status: str, **details):
        """Log an operation with status"""
        msg = f"Operation: {operation} | Status: {status}"
        if details:
            msg += f" | Details: {details}"
        
        if status == "success":
            self.info(msg)
        elif status == "failed":
            self.error(msg, component=operation)
        else:
            self.warning(msg)


# Global logger instance
logger = AutoContentLogger()
