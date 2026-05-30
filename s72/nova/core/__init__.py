"""NOVA Core — runtime foundation, config, structured logging."""

from .config import Config, ConfigWatcher, SourceConfig, AIConfig, AIProviderConfig
from .logging import LogEntry, Logger, VisibilityStack, VISIBILITY, log, action
from .runtime import Runtime
from .auto import AutoDiscover, AutoRouter, AutoUIRenderer
from .tester import AutoTester, TestResult, TestSuite

__all__ = [
    "Config", "ConfigWatcher", "SourceConfig", "AIConfig", "AIProviderConfig",
    "LogEntry", "Logger", "VisibilityStack", "VISIBILITY", "log", "action",
    "Runtime",
    "AutoDiscover", "AutoRouter", "AutoUIRenderer",
    "AutoTester", "TestResult", "TestSuite",
]
