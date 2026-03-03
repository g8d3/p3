#!/usr/bin/env python3
"""
AI Content Factory - Scheduler
Automated scheduling with cron
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import shutil

class ContentScheduler:
    def __init__(self, config_dir="~/.config/ai-content-factory"):
        self.config_dir = os.path.expanduser(config_dir)
        self.data_dir = os.path.join(self.config_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.schedule_file = os.path.join(self.data_dir, "schedule.json")
        self.load_schedule()
    
    def load_schedule(self):
        """Load schedule from file"""
        if os.path.exists(self.schedule_file):
            with open(self.schedule_file, 'r') as f:
                self.schedule = json.load(f)
        else:
            self.schedule = []
    
    def save_schedule(self):
        """Save schedule to file"""
        with open(self.schedule_file, 'w') as f:
            json.dump(self.schedule, f, indent=2)
    
    def add_task(self, task_type, time_spec, task_config):
        """
        Add a scheduled task
        
        time_spec: cron-style (e.g., "0 9 * * *" = 9am daily)
        """
        task = {
            "id": f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": task_type,
            "time": time_spec,
            "config": task_config,
            "enabled": True,
            "created": datetime.now().isoformat()
        }
        
        self.schedule.append(task)
        self.save_schedule()
        
        return task
    
    def remove_task(self, task_id):
        """Remove a scheduled task"""
        self.schedule = [t for t in self.schedule if t.get("id") != task_id]
        self.save_schedule()
    
    def list_tasks(self):
        """List all scheduled tasks"""
        return self.schedule
    
    def setup_cron(self):
        """Set up cron jobs for all enabled tasks"""
        # Get the path to the content factory scripts
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Clear existing ai-content cron jobs
        self._clear_cron_jobs()
        
        # Add new cron jobs
        for task in self.schedule:
            if not task.get("enabled", True):
                continue
            
            time_spec = task["time"]
            task_type = task["type"]
            
            # Build command based on task type
            if task_type == "generate_topics":
                cmd = f"cd {script_dir} && python3 topic_generator.py ai 7 >> /tmp/ai-content.log 2>&1"
            elif task_type == "record":
                cmd = f"cd {script_dir} && python3 main.py --record --topic-id {task['config'].get('topic_id', '')}"
            elif task_type == "process":
                cmd = f"cd {script_dir} && python3 main.py --process"
            elif task_type == "upload":
                cmd = f"cd {script_dir} && python3 main.py --upload"
            elif task_type == "full_pipeline":
                cmd = f"cd {script_dir} && python3 main.py --full"
            else:
                continue
            
            # Add to crontab
            cron_line = f"{time_spec} {cmd}"
            self._add_cron_line(cron_line)
        
        print(f"Set up {len([t for t in self.schedule if t.get('enabled', True)])} cron tasks")
    
    def _clear_cron_jobs(self):
        """Clear existing ai-content cron jobs"""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                new_lines = [l for l in lines if 'ai-content' not in l]
                
                if new_lines:
                    new_crontab = '\n'.join(new_lines)
                    subprocess.run(
                        ["crontab", "-"],
                        input=new_crontab,
                        text=True
                    )
        except:
            pass
    
    def _add_cron_line(self, line):
        """Add a line to crontab"""
        # Read current crontab
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                current = result.stdout
            else:
                current = ""
        except:
            current = ""
        
        # Add new line
        new_crontab = current.strip() + '\n' + line + '\n'
        
        # Write back
        subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            text=True
        )
    
    def get_next_runs(self):
        """Get next scheduled run times (approximate)"""
        runs = []
        
        for task in self.schedule:
            if not task.get("enabled", True):
                continue
            
            time_spec = task["time"]
            task_type = task["type"]
            
            # Parse simple cron specs
            # This is simplified - real cron parsing would be more complex
            parts = time_spec.split()
            
            if len(parts) >= 5:
                runs.append({
                    "id": task["id"],
                    "type": task_type,
                    "time_spec": time_spec,
                    "next_approx": "Check crontab"
                })
        
        return runs


# Predefined schedules
class PresetSchedules:
    """Common scheduling patterns"""
    
    @staticmethod
    def daily_morning():
        """Daily at 9 AM"""
        return "0 9 * * *"
    
    @staticmethod
    def daily_evening():
        """Daily at 7 PM"""
        return "0 19 * * *"
    
    @staticmethod
    def weekdays_morning():
        """Mon-Fri at 8 AM"""
        return "0 8 * * 1-5"
    
    @staticmethod
    def twice_weekly():
        """Tuesday and Thursday"""
        return "0 18 * * 2,4"
    
    @staticmethod
    def weekly_sunday():
        """Sunday at 10 AM"""
        return "0 10 * * 0"


def setup_weekly_schedule(scheduler):
    """Set up a typical weekly content schedule"""
    
    # Sunday: Generate topics for the week
    scheduler.add_task(
        "generate_topics",
        PresetSchedules.weekly_sunday(),
        {"count": 7}
    )
    
    # Daily at 10 AM: Record content
    scheduler.add_task(
        "full_pipeline",
        "0 10 * * *",
        {}
    )
    
    scheduler.setup_cron()
    
    print("Weekly schedule set up:")
    print("  - Sunday 10AM: Generate topics")
    print("  - Daily 10AM: Full content pipeline")


def show_schedule():
    """Show current schedule"""
    scheduler = ContentScheduler()
    
    print("\n=== Content Factory Schedule ===\n")
    
    tasks = scheduler.list_tasks()
    
    if not tasks:
        print("No tasks scheduled. Run setup to configure.")
        return
    
    for task in tasks:
        status = "✓" if task.get("enabled", True) else "✗"
        print(f"{status} [{task['type']}] {task['time']}")
        print(f"   Config: {task.get('config', {})}\n")
    
    print("\nNext approximate runs:")
    for run in scheduler.get_next_runs():
        print(f"  - {run['type']}: {run['time_spec']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_schedule()
    elif len(sys.argv) > 1 and sys.argv[1] == "setup":
        scheduler = ContentScheduler()
        setup_weekly_schedule(scheduler)
    else:
        print("Usage: python3 scheduler.py [show|setup]")
        print("  show   - Show current schedule")
        print("  setup  - Set up weekly content schedule")
