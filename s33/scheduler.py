"""
AutoContent - Task Scheduler
Schedules and manages automated content creation tasks
"""

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional
from logger import logger
from error_handler import self_healer, ErrorContext


@dataclass
class ScheduledTask:
    """A scheduled task"""
    name: str
    func: Callable
    interval_hours: float
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0


class TaskScheduler:
    """Task scheduler for automated content creation"""
    
    def __init__(self, check_interval_minutes: int = 30):
        self.check_interval = check_interval_minutes * 60
        self.tasks: list[ScheduledTask] = []
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
    
    def add_task(self, name: str, func: Callable, interval_hours: float):
        """Add a scheduled task"""
        task = ScheduledTask(
            name=name,
            func=func,
            interval_hours=interval_hours,
            next_run=datetime.now()
        )
        self.tasks.append(task)
        logger.info(f"Added task: {name} (every {interval_hours}h)")
    
    def remove_task(self, name: str):
        """Remove a task"""
        self.tasks = [t for t in self.tasks if t.name != name]
        logger.info(f"Removed task: {name}")
    
    def enable_task(self, name: str):
        """Enable a task"""
        for task in self.tasks:
            if task.name == name:
                task.enabled = True
                logger.info(f"Enabled task: {name}")
    
    def disable_task(self, name: str):
        """Disable a task"""
        for task in self.tasks:
            if task.name == name:
                task.enabled = False
                logger.info(f"Disabled task: {name}")
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                self._check_and_run_tasks()
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_and_run_tasks(self):
        """Check and run due tasks"""
        now = datetime.now()
        
        for task in self.tasks:
            if not task.enabled:
                continue
            
            if task.next_run and now >= task.next_run:
                self._run_task(task)
    
    def _run_task(self, task: ScheduledTask):
        """Run a single task"""
        logger.info(f"Running task: {task.name}")
        
        task.last_run = datetime.now()
        task.run_count += 1
        
        try:
            # Run with self-healing
            context = ErrorContext(
                operation=task.name,
                component="scheduler",
                error=Exception("placeholder"),
                max_attempts=3
            )
            
            success, _ = self_healer.handle_with_healing(
                task.name,
                "scheduler",
                task.func
            )
            
            if success:
                task.success_count += 1
                logger.log_operation(task.name, "success")
            else:
                task.failure_count += 1
                logger.log_operation(task.name, "failed")
                
        except Exception as e:
            task.failure_count += 1
            logger.error(f"Task {task.name} failed: {e}")
        
        # Schedule next run
        task.next_run = datetime.now() + timedelta(hours=task.interval_hours)
        logger.info(f"Task {task.name} next run: {task.next_run}")
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            "running": self.running,
            "tasks": [
                {
                    "name": t.name,
                    "enabled": t.enabled,
                    "interval_hours": t.interval_hours,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "next_run": t.next_run.isoformat() if t.next_run else None,
                    "run_count": t.run_count,
                    "success_count": t.success_count,
                    "failure_count": t.failure_count
                }
                for t in self.tasks
            ]
        }
    
    def run_now(self, name: str):
        """Manually run a task"""
        for task in self.tasks:
            if task.name == name:
                self._run_task(task)
                return True
        return False


def create_scheduler(**kwargs) -> TaskScheduler:
    """Factory function"""
    return TaskScheduler(**kwargs)
