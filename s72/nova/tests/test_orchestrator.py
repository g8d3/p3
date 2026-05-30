"""Tests for multi-agent orchestration."""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from nova.ipc import AgentScheduler, Task, TaskStatus, TokenBucket


class TestTokenBucket:
    def test_consume(self):
        bucket = TokenBucket(10, 10)
        assert bucket.consume(5) is True
        assert bucket.consume(5) is True
        assert bucket.consume(1) is False  # depleted

    def test_refill(self):
        import time
        bucket = TokenBucket(10, 10)
        bucket.consume(10)
        time.sleep(0.11)  # enough for 1 token refill
        assert bucket.consume(1) is True  # should have refilled 1 token

    def test_wait_time(self):
        bucket = TokenBucket(10, 10)
        bucket.consume(10)
        wait = bucket.wait_time(5)
        assert wait > 0.4  # need 0.5s for 5 tokens at 10 TPS


class TestTask:
    def test_task_creation(self):
        task = Task(agent="worker", action="generate_script",
                     params={"topic": "AI"}, priority=1)
        assert task.id.startswith("task_")
        assert task.status == TaskStatus.PENDING
        assert task.can_retry is True

    def test_task_expiry(self):
        import time
        task = Task(agent="worker", action="test", timeout_s=0.1)
        task.started_at = time.time() - 1
        assert task.is_expired is True

    def test_to_dict(self):
        task = Task(agent="test", action="echo")
        d = task.to_dict()
        assert d["agent"] == "test"
        assert d["action"] == "echo"
        assert d["status"] == "pending"


class TestAgentScheduler:
    @pytest.mark.asyncio
    async def test_register_and_schedule(self):
        scheduler = AgentScheduler()
        scheduler.register_agent("worker1", actions=["echo"], tps_budget=100)

        results = []
        async def echo_handler(task):
            results.append(task.params)
            return task.params

        scheduler.on_action("echo", echo_handler)

        task = scheduler.create_task("worker1", "echo", {"msg": "hello"})
        assert task.id in scheduler._tasks

        # Run one cycle
        ready = scheduler.resolve_dag()
        assert len(ready) == 1
        assert ready[0].id == task.id

    @pytest.mark.asyncio
    async def test_dependency_resolution(self):
        scheduler = AgentScheduler()
        scheduler.register_agent("w1", ["step1", "step2"])

        results = []
        async def handler(task):
            results.append(task.action)
            return task.action

        scheduler.on_action("step1", handler)
        scheduler.on_action("step2", handler)

        t1 = scheduler.create_task("w1", "step1")
        t2 = scheduler.create_task("w1", "step2", depends_on=[t1.id])

        # Before t1 completes: only step1 should be ready
        ready = scheduler.resolve_dag()
        assert len(ready) == 1
        assert ready[0].action == "step1"

        # Complete t1
        t1.status = TaskStatus.DONE
        ready = scheduler.resolve_dag()
        assert len(ready) == 1
        assert ready[0].action == "step2"

    @pytest.mark.asyncio
    async def test_retry_and_fallback(self):
        scheduler = AgentScheduler()
        scheduler.register_agent("w1", ["fragile", "fallback_handler"])

        call_count = 0
        async def fragile(task):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Not yet")
            return "ok"

        scheduler.on_action("fragile", fragile)

        task = scheduler.create_task("w1", "fragile", max_retries=2)
        await scheduler._execute_task(task)
        assert task.status == TaskStatus.DONE
        assert call_count == 3  # 2 retries + 1 success

    @pytest.mark.asyncio
    async def test_agent_selection(self):
        scheduler = AgentScheduler()
        scheduler.register_agent("slow", ["action_x"], tps_budget=1)
        scheduler.register_agent("fast", ["action_x"], tps_budget=100)

        best = scheduler._find_best_agent("action_x")
        assert best == "fast"  # fast has more TPS budget

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        scheduler = AgentScheduler()
        scheduler.register_agent("worker1", ["fetch", "process", "save"])

        pipeline = []
        async def handler(task):
            pipeline.append(task.action)
            return task.action

        scheduler.on_action("fetch", handler)
        scheduler.on_action("process", handler)
        scheduler.on_action("save", handler)

        t1 = scheduler.create_task("worker1", "fetch", priority=10)
        t2 = scheduler.create_task("worker1", "process", depends_on=[t1.id])
        t3 = scheduler.create_task("worker1", "save", depends_on=[t2.id])

        # Execute sequentially
        await scheduler._execute_task(t1)
        assert t1.status == TaskStatus.DONE

        await scheduler._execute_task(t2)
        assert t2.status == TaskStatus.DONE

        await scheduler._execute_task(t3)
        assert t3.status == TaskStatus.DONE

        assert pipeline == ["fetch", "process", "save"]

    def test_status_report(self):
        scheduler = AgentScheduler()
        scheduler.register_agent("w1", ["test"])
        status = scheduler.get_status()
        assert "agents" in status
        assert "w1" in status["agents"]
        assert status["queue_size"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
