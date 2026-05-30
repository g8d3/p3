"""Multi-Agent Orchestration — token-aware task scheduling with DAG resolution.

Agents register capabilities. The orchestrator schedules tasks across
agents respecting dependency order and provider token limits (TPS).
"""

from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from collections import deque

from ..core import VISIBILITY


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    FALLBACK = "fallback"


@dataclass
class Task:
    """A unit of work for an agent."""
    id: str = ""
    agent: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)
    priority: int = 0  # Higher = more urgent
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 2
    timeout_s: float = 120
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    result: Any = None
    error: str = ""
    tokens_used: int = 0
    fallback_action: str = ""
    _dependents: list[str] = field(default_factory=list, repr=False)

    def __post_init__(self):
        if not self.id:
            self.id = f"task_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def duration_s(self) -> float:
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        if self.started_at:
            return time.time() - self.started_at
        return 0.0

    @property
    def is_expired(self) -> bool:
        if self.started_at and time.time() - self.started_at > self.timeout_s:
            return True
        return False

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent": self.agent,
            "action": self.action,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "timeout_s": self.timeout_s,
            "duration_s": self.duration_s,
            "error": self.error,
            "tokens_used": self.tokens_used,
        }


@dataclass
class AgentCapability:
    """What an agent can do."""
    agent_id: str
    actions: list[str]
    max_concurrent: int = 3
    tps_budget: float = 10.0  # Tokens per second allocated
    current_load: int = 0
    total_tokens_used: int = 0


class TokenBucket:
    """Token bucket rate limiter — tracks TPS consumption."""

    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    def consume(self, tokens: float) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_time(self, tokens: float) -> float:
        if self.tokens >= tokens:
            return 0
        needed = tokens - self.tokens
        return needed / self.refill_rate if self.refill_rate > 0 else float('inf')


class AgentScheduler:
    """Schedules tasks across agents with dependency resolution and TPS awareness."""

    def __init__(self):
        self._agents: dict[str, AgentCapability] = {}
        self._tasks: dict[str, Task] = {}
        self._queue: list[Task] = []
        self._running: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._handlers: dict[str, Callable] = {}
        self._token_buckets: dict[str, TokenBucket] = {}
        self._completed: deque[Task] = deque(maxlen=1000)

    def register_agent(self, agent_id: str, actions: list[str],
                       max_concurrent: int = 3, tps_budget: float = 10.0):
        """Register an agent with its capabilities."""
        self._agents[agent_id] = AgentCapability(
            agent_id=agent_id,
            actions=actions,
            max_concurrent=max_concurrent,
            tps_budget=tps_budget,
        )
        self._token_buckets[agent_id] = TokenBucket(tps_budget, tps_budget)
        VISIBILITY.action("scheduler.register",
                          f"Agent {agent_id} ({len(actions)} actions, {tps_budget} TPS)")
        return agent_id

    def on_action(self, action: str, handler: Callable):
        """Register a handler for a specific action."""
        self._handlers[action] = handler

    def add_task(self, task: Task) -> str:
        """Add a task to the queue."""
        self._tasks[task.id] = task
        self._queue.append(task)
        VISIBILITY.log("DEBUG", "scheduler", f"Task queued: {task.action} → {task.agent}",
                       {"task_id": task.id, "priority": task.priority})
        return task.id

    def create_task(self, agent: str, action: str, params: dict = None,
                    priority: int = 0, depends_on: list[str] = None,
                    max_retries: int = 2, timeout_s: float = 120,
                    fallback_action: str = "") -> Task:
        """Create and add a task."""
        task = Task(
            agent=agent,
            action=action,
            params=params or {},
            priority=priority,
            depends_on=depends_on or [],
            max_retries=max_retries,
            timeout_s=timeout_s,
            fallback_action=fallback_action,
        )
        self.add_task(task)
        return task

    def resolve_dag(self) -> list[Task]:
        """Resolve the DAG: return tasks whose dependencies are met."""
        ready = []
        for task in self._queue:
            if task.status != TaskStatus.PENDING:
                continue
            # Check dependencies
            deps_met = all(
                dep_id in self._tasks and
                self._tasks[dep_id].status in (TaskStatus.DONE, TaskStatus.SKIPPED)
                for dep_id in task.depends_on
            )
            if deps_met:
                ready.append(task)
        return ready

    def _find_best_agent(self, action: str) -> Optional[str]:
        """Find the best agent for an action based on load + TPS."""
        candidates = []
        for agent_id, cap in self._agents.items():
            if action in cap.actions and cap.current_load < cap.max_concurrent:
                bucket = self._token_buckets.get(agent_id)
                wait = bucket.wait_time(100) if bucket else 0  # estimate 100 tokens
                candidates.append((wait, cap.current_load, agent_id))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1]))
        return candidates[0][2]

    async def _execute_task(self, task: Task):
        """Execute a single task with retry and fallback."""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        agent = self._agents.get(task.agent)
        if agent:
            agent.current_load += 1

        handler = self._handlers.get(task.action)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for action: {task.action}"
            VISIBILITY.log("ERROR", "scheduler", task.error, {"task_id": task.id})
            self._finalize(task, agent)
            return

        for attempt in range(task.max_retries + 1):
            try:
                # Wait for token budget
                bucket = self._token_buckets.get(task.agent)
                if bucket:
                    wait = bucket.wait_time(200)  # estimate
                    if wait > 0:
                        await asyncio.sleep(min(wait, 10))

                result = await handler(task)
                task.status = TaskStatus.DONE
                task.result = result
                task.completed_at = time.time()
                if bucket:
                    bucket.consume(200)

                VISIBILITY.log("INFO", "scheduler",
                               f"Task done: {task.action}", task.to_dict())
                self._finalize(task, agent)
                return

            except Exception as e:
                task.retry_count = attempt + 1
                task.error = str(e)
                if attempt < task.max_retries:
                    wait = min(2 ** attempt, 30)
                    VISIBILITY.log("WARN", "scheduler",
                                   f"Retry {attempt+1}/{task.max_retries} for {task.action}",
                                   {"task_id": task.id, "wait_s": wait, "error": str(e)})
                    await asyncio.sleep(wait)
                else:
                    # Try fallback
                    if task.fallback_action and task.fallback_action in self._handlers:
                        VISIBILITY.action("scheduler.fallback",
                                          f"Using fallback for {task.action}")
                        try:
                            fallback_handler = self._handlers[task.fallback_action]
                            result = await fallback_handler(task)
                            task.status = TaskStatus.FALLBACK
                            task.result = result
                            task.completed_at = time.time()
                            self._finalize(task, agent)
                            return
                        except Exception as fb_e:
                            task.error += f" | Fallback failed: {fb_e}"

                    task.status = TaskStatus.FAILED
                    task.completed_at = time.time()
                    VISIBILITY.log("ERROR", "scheduler",
                                   f"Task failed: {task.action}", task.to_dict())
                    self._finalize(task, agent)

    def _finalize(self, task: Task, agent: Optional[AgentCapability]):
        if agent:
            agent.current_load = max(0, agent.current_load - 1)
            agent.total_tokens_used += task.tokens_used
        # Remove from queue
        if task in self._queue:
            self._queue.remove(task)
        self._completed.append(task)
        # Trigger dependents
        for t in list(self._queue):
            if task.id in t.depends_on:
                t.depends_on.remove(task.id)

    async def run_loop(self, interval: float = 0.5):
        """Main scheduling loop."""
        self._running = True
        self._loop = asyncio.get_running_loop()
        VISIBILITY.action("scheduler.start", "Scheduler loop started")

        while self._running:
            ready = self.resolve_dag()
            # Sort by priority (highest first)
            ready.sort(key=lambda t: t.priority, reverse=True)

            for task in ready:
                agent = self._find_best_agent(task.action)
                if agent:
                    task.agent = agent
                    asyncio.create_task(self._execute_task(task))
                else:
                    # No agent available, leave in queue
                    pass

            if not ready and not self._queue:
                # Nothing to do: brief sleep to prevent CPU spin
                await asyncio.sleep(interval)
            else:
                await asyncio.sleep(interval / 2)

    def stop(self):
        self._running = False

    def get_status(self) -> dict:
        return {
            "agents": {
                aid: {
                    "actions": cap.actions,
                    "load": f"{cap.current_load}/{cap.max_concurrent}",
                    "tokens_used": cap.total_tokens_used,
                }
                for aid, cap in self._agents.items()
            },
            "queue_size": len(self._queue),
            "completed": len(self._completed),
            "running": self._running,
        }

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_recent(self, n: int = 20) -> list[Task]:
        return list(self._completed)[-n:]


class Orchestrator:
    """High-level orchestrator — creates tasks, schedules them, reports results.

    Integrates the scheduler with the IPC bus and AI adapter.
    """

    def __init__(self, scheduler: AgentScheduler, ipc_bus: "IPCBus" = None):
        self.scheduler = scheduler
        self.ipc_bus = ipc_bus
        self._pipelines: dict[str, list[Task]] = {}

    def create_pipeline(self, pipeline_id: str, tasks: list[Task]):
        """Register a pipeline (sequence of dependent tasks)."""
        self._pipelines[pipeline_id] = tasks
        for task in tasks:
            self.scheduler.add_task(task)
        VISIBILITY.action("pipeline.create",
                          f"Pipeline {pipeline_id}: {len(tasks)} tasks")
        return pipeline_id

    def get_pipeline_status(self, pipeline_id: str) -> list[dict]:
        tasks = self._pipelines.get(pipeline_id, [])
        return [t.to_dict() for t in tasks]

    async def run_agent_task(self, agent_id: str, task: Task) -> Any:
        """Route a task to the agent via IPC bus."""
        if self.ipc_bus and agent_id in self.ipc_bus._agents:
            from ..ipc import TaskMessage
            msg = TaskMessage(
                agent=agent_id,
                payload={"action": task.action, "params": task.params},
            )
            self.ipc_bus.send(agent_id, msg)
            return {"status": "dispatched", "message_id": msg.id}
        raise RuntimeError(f"Agent {agent_id} not available")

    async def run_local(self, action: str, params: dict = None) -> Any:
        """Run an action locally (same process)."""
        handler = self.scheduler._handlers.get(action)
        if handler:
            task = Task(agent="local", action=action, params=params or {})
            return await handler(task)
        raise RuntimeError(f"No handler for action: {action}")
