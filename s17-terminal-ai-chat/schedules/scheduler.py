"""Scheduler for automated tasks."""

import threading
import time
import sched
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass


@dataclass
class ScheduledTask:
    """Scheduled task representation."""
    
    id: str
    name: str
    agent_id: str
    prompt: str
    schedule_type: str
    schedule_value: str
    enabled: bool
    last_run: Optional[str]
    callback: Optional[Callable] = None
    
    def get_next_run(self) -> Optional[datetime]:
        """Calculate next run time."""
        if not self.enabled:
            return None
        
        now = datetime.now()
        
        if self.schedule_type == "interval":
            try:
                minutes = int(self.schedule_value)
                return now + timedelta(minutes=minutes)
            except ValueError:
                return None
        
        elif self.schedule_type == "hourly":
            return now + timedelta(hours=1)
        
        elif self.schedule_type == "daily":
            return now + timedelta(days=1)
        
        elif self.schedule_type == "weekly":
            return now + timedelta(weeks=1)
        
        return None


class Scheduler:
    """Task scheduler for automated AI tasks."""
    
    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def add_task(self, task: ScheduledTask):
        """Add a task to the scheduler."""
        self.tasks[task.id] = task
        self._schedule_task(task)
    
    def remove_task(self, task_id: str):
        """Remove a task from the scheduler."""
        if task_id in self.tasks:
            del self.tasks[task_id]
    
    def _schedule_task(self, task: ScheduledTask):
        """Schedule a single task."""
        if not task.enabled:
            return
        
        next_run = task.get_next_run()
        if next_run:
            delay = (next_run - datetime.now()).total_seconds()
            if delay > 0:
                self.scheduler.enter(delay, 1, self._run_task, (task,))
    
    def _run_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        if task.callback:
            try:
                task.callback(task)
                task.last_run = datetime.now().isoformat()
            except Exception as e:
                print(f"Error running task {task.name}: {e}")
        
        self._schedule_task(task)
    
    def start(self):
        """Start the scheduler."""
        self.running = True
        self.thread = threading.Thread(target=self.scheduler.run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self.scheduler.clear()
    
    def get_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks."""
        return list(self.tasks.values())
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a specific task."""
        return self.tasks.get(task_id)
    
    def run_now(self, task_id: str):
        """Run a task immediately."""
        task = self.tasks.get(task_id)
        if task and task.callback:
            threading.Thread(target=task.callback, args=(task,)).start()
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self.running,
            "task_count": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled)
        }
