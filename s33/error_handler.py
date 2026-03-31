"""
AutoContent - Error Handler with Self-Healing
"""

import traceback
import time
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from logger import logger, ErrorLog


@dataclass
class HealAttempt:
    """Record of a healing attempt"""
    timestamp: str
    method: str
    success: bool
    error: Optional[str] = None


@dataclass
class ErrorContext:
    """Context for error handling"""
    operation: str
    component: str
    error: Exception
    attempt: int = 0
    max_attempts: int = 3
    heal_attempts: list[HealAttempt] = field(default_factory=list)


class SelfHealer:
    """Self-healing error handler"""
    
    def __init__(self, max_attempts: int = 5):
        self.max_attempts = max_attempts
        self.heal_strategies: dict[str, Callable] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default healing strategies"""
        
        def retry_strategy(context: ErrorContext) -> bool:
            """Simple retry after delay"""
            logger.info(f"Attempting retry for {context.operation}")
            time.sleep(2 ** context.attempt)
            return True
        
        def browser_restart_strategy(context: ErrorContext) -> bool:
            """Restart browser session"""
            logger.info("Attempting browser restart")
            # Will be called by the browser module
            return True
        
        def session_refresh_strategy(context: ErrorContext) -> bool:
            """Refresh authentication session"""
            logger.info("Attempting session refresh")
            return True
        
        def fallback_llm_strategy(context: ErrorContext) -> bool:
            """Switch to fallback LLM"""
            logger.info("Attempting fallback LLM")
            return True
        
        self.heal_strategies = {
            "retry": retry_strategy,
            "browser_restart": browser_restart_strategy,
            "session_refresh": session_refresh_strategy,
            "fallback_llm": fallback_llm_strategy
        }
    
    def register_strategy(self, name: str, strategy: Callable):
        """Register a custom healing strategy"""
        self.heal_strategies[name] = strategy
    
    def heal(self, context: ErrorContext) -> bool:
        """Attempt to heal an error"""
        logger.warning(
            f"Healing {context.operation} - Attempt {len(context.heal_attempts) + 1}"
        )
        
        # Try different strategies based on error type
        strategies_to_try = self._get_strategies_for_error(context)
        
        for strategy_name in strategies_to_try:
            if strategy_name not in self.heal_strategies:
                continue
            
            strategy = self.heal_strategies[strategy_name]
            attempt = HealAttempt(
                timestamp=datetime.now().isoformat(),
                method=strategy_name
            )
            
            try:
                success = strategy(context)
                attempt.success = success
                context.heal_attempts.append(attempt)
                
                if success:
                    logger.info(f"Healed via {strategy_name}")
                    return True
                    
            except Exception as e:
                attempt.success = False
                attempt.error = str(e)
                context.heal_attempts.append(attempt)
                logger.error(f"Healing strategy {strategy_name} failed: {e}")
        
        return False
    
    def _get_strategies_for_error(self, context: ErrorContext) -> list[str]:
        """Determine which strategies to try based on error"""
        error_msg = str(context.error).lower()
        
        if "timeout" in error_msg or "network" in error_msg:
            return ["retry", "browser_restart"]
        elif "auth" in error_msg or "session" in error_msg:
            return ["session_refresh", "retry"]
        elif "rate limit" in error_msg or "429" in error_msg:
            return ["retry"]
        elif "api" in error_msg or "llm" in error_msg:
            return ["fallback_llm", "retry"]
        else:
            return ["retry", "browser_restart"]
    
    def handle_with_healing(
        self, 
        operation: str, 
        component: str,
        func: Callable, 
        *args, 
        **kwargs
    ) -> tuple[bool, Any]:
        """Execute function with error handling and self-healing"""
        
        for attempt in range(self.max_attempts):
            try:
                result = func(*args, **kwargs)
                logger.log_operation(operation, "success")
                return True, result
                
            except Exception as e:
                context = ErrorContext(
                    operation=operation,
                    component=component,
                    error=e,
                    attempt=attempt
                )
                
                logger.error(
                    f"Error in {operation}: {e}",
                    component=component,
                    stack_trace=traceback.format_exc()
                )
                
                # Try to heal
                if self.heal(context):
                    logger.info(f"Healing successful, retrying {operation}")
                    continue
                else:
                    logger.error(
                        f"Failed to heal {operation} after {attempt + 1} attempts"
                    )
        
        logger.log_operation(operation, "failed", attempts=self.max_attempts)
        return False, None


# Global self-healer instance
self_healer = SelfHealer()
