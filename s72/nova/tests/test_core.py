"""Tests for NOVA framework core."""

from __future__ import annotations
import os
import sys
import tempfile
import pytest

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nova.core import Config, ConfigWatcher, VISIBILITY, Logger
from nova.ipc import IPCBus, Message, MessageType, TaskMessage, ResultMessage
from nova.meta import Spec, parse_spec, CodeGenerator
from nova.meta.spec import ModelSpec, FieldSpec, RouteSpec


class TestConfig:
    def test_default_config(self):
        cfg = Config()
        assert cfg.name == "nova-app"
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8777

    def test_update_config(self):
        cfg = Config(name="test")
        assert cfg.name == "test"
        updates = []
        cfg.register_callback(lambda c: updates.append("changed"))
        cfg.update({"port": 9999, "host": "127.0.0.1"})
        assert cfg.port == 9999
        assert cfg.host == "127.0.0.1"
        assert updates == ["changed"]

    def test_dict(self):
        cfg = Config(name="test")
        d = cfg.dict()
        assert d["name"] == "test"
        assert "ai" in d


class TestLogging:
    def test_logger(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = Logger(tmp)
            entry = logger.info("test", "hello world")
            assert entry.level == "INFO"
            assert entry.message == "hello world"
            assert entry.source == "test"

    def test_visibility_stack(self):
        v = VISIBILITY
        v.action("test.action", "testing")
        actions = v.get_actions(1)
        assert len(actions) >= 1
        assert actions[0]["kind"] == "test.action"


class TestIPC:
    def test_message_creation(self):
        msg = Message(type=MessageType.TASK, agent="test-agent",
                       payload={"action": "generate", "params": {"topic": "AI"}})
        assert msg.id.startswith("msg_")
        assert msg.type == MessageType.TASK
        assert msg.payload.get("action") == "generate"

    def test_task_message(self):
        msg = TaskMessage(agent="orchestrator",
                          payload={"action": "test", "params": {"x": 1}})
        assert msg.action == "test"
        assert msg.params == {"x": 1}

    def test_message_serialization(self):
        msg = Message(type=MessageType.RESULT, agent="worker1",
                       payload={"status": "ok", "output": "done"})
        json_str = msg.to_json()
        restored = Message.from_json(json_str)
        assert restored.id == msg.id
        assert restored.type == MessageType.RESULT
        assert restored.payload["status"] == "ok"

    def test_ipc_bus(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = IPCBus(tmp)
            io = bus.register_agent("test-agent")
            assert io.agent_id == "test-agent"

            msg = TaskMessage(agent="orchestrator",
                              payload={"action": "test", "params": {}})
            bus.send("test-agent", msg)

            received = io.read_inbox()
            assert len(received) >= 1
            assert received[0].id == msg.id


class TestSpec:
    @pytest.fixture
    def sample_yaml(self, tmp_path):
        path = tmp_path / "app.yaml"
        path.write_text("""
name: test-app
version: "1.0.0"
description: Test app

models:
  - name: User
    fields:
      name: {type: string, required: true}
      email: {type: email, unique: true}

routes:
  - pattern: /api/users
    methods: [GET, POST]
    model: User

ai:
  capabilities: [generate_script, summarize]
""")
        return str(path)

    def test_parse_spec(self, sample_yaml):
        spec = parse_spec(sample_yaml)
        assert spec.name == "test-app"
        assert spec.version == "1.0.0"
        assert len(spec.models) == 1
        assert spec.models[0].name == "User"
        assert len(spec.models[0].fields) == 2
        assert len(spec.routes) == 1
        assert "generate_script" in spec.ai.capabilities

    def test_codegen(self, sample_yaml):
        spec = parse_spec(sample_yaml)
        gen = CodeGenerator()
        files = gen.generate_all(spec)
        assert any("models/user.py" in f for f in files)
        assert any("routes/api.py" in f for f in files)
        assert any("tests/" in f for f in files)
        assert "main.py" in files


class TestAIAdapter:
    def test_adapter_creation(self):
        from nova.ai import AIAdapter
        config = Config()
        adapter = AIAdapter(config)
        assert adapter._cache_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
