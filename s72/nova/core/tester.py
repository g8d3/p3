"""Auto-Test Suite — NOVA tests itself on every startup and reports regressions.

Every endpoint is automatically tested when the framework boots.
Failures are logged to the visibility stack and exposed in DevTools.
The evolution engine can use failures to propose fixes.
"""

from __future__ import annotations
import asyncio
import json
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

from ..core import VISIBILITY


@dataclass
class TestResult:
    name: str = ""
    endpoint: str = ""
    method: str = "GET"
    status: str = "pending"  # pending | running | passed | failed | skipped
    expected_status: int = 200
    actual_status: int = 0
    latency_ms: float = 0.0
    error: str = ""
    response_sample: str = ""


@dataclass
class TestSuite:
    name: str = ""
    results: list[TestResult] = field(default_factory=list)
    started_at: float = 0.0
    completed_at: float = 0.0
    _passed: int = 0
    _failed: int = 0
    _skipped: int = 0

    @property
    def duration_s(self) -> float:
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return 0.0

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    def summary(self) -> dict:
        return {
            "name": self.name,
            "total": len(self.results),
            "passed": self.passed,
            "failed": self.failed,
            "duration_s": self.duration_s,
        }


class AutoTester:
    """Self-testing system — tests all endpoints automatically.

    Runs on startup and periodically. Reports failures to visibility stack.
    Can be extended with custom test handlers.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8777"):
        self.base_url = base_url.rstrip("/")
        self._custom_tests: list[dict] = []
        self._suites: list[TestSuite] = []
        self._running = False

    def add_test(self, endpoint: str, method: str = "GET",
                 expected_status: int = 200,
                 name: str = "", body: dict = None,
                 headers: dict = None) -> None:
        """Register a custom endpoint test."""
        self._custom_tests.append({
            "endpoint": endpoint,
            "method": method,
            "expected_status": expected_status,
            "name": name or f"{method} {endpoint}",
            "body": body,
            "headers": headers or {},
        })

    def add_handler(self, name: str, handler: Callable) -> None:
        """Add a custom test handler (async function that returns TestResult)."""
        self._custom_tests.append({
            "handler": handler,
            "name": name,
        })

    def discover_endpoints(self, spec: Any = None) -> list[dict]:
        """Discover endpoints to test from spec + runtime."""
        tests = list(self._custom_tests)

        # Common API endpoints
        common = [
            ("/api/health", "GET", 200),
            ("/api/status", "GET", 200),
            ("/api/config", "GET", 200),
            ("/api/visibility/actions", "GET", 200),
            ("/api/visibility/errors", "GET", 200),
            ("/api/visibility/status", "GET", 200),
        ]
        for endpoint, method, expected in common:
            tests.append({
                "endpoint": endpoint, "method": method,
                "expected_status": expected,
                "name": f"{method} {endpoint}",
            })

        # Auto-UI pages
        ui_pages = ["/", "/auto/ui", "/__dev"]
        for page in ui_pages:
            tests.append({
                "endpoint": page, "method": "GET",
                "expected_status": 200,
                "name": f"GET {page}",
                "check_html": True,
            })

        # Auto-generated API routes
        auto_api = ["/api/users", "/api/videos", "/api/posts",
                     "/api/feed", "/auto/api/users"]
        for ep in auto_api:
            tests.append({
                "endpoint": ep, "method": "GET",
                "expected_status": 200,
                "name": f"GET {ep}",
            })

        # Config update (POST)
        tests.append({
            "endpoint": "/api/config", "method": "POST",
            "expected_status": 200,
            "name": "POST /api/config",
            "body": {"voice": "test-voice"},
            "check_json_keys": ["status"],
        })

        return tests

    async def _request(self, method: str, url: str, data: bytes = None,
                        headers: dict = None, timeout: int = 10) -> tuple:
        """Non-blocking HTTP request using thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self._do_request(method, url, data, headers, timeout))

    def _do_request(self, method: str, url: str, data: bytes = None,
                     headers: dict = None, timeout: int = 10) -> tuple:
        """Synchronous HTTP request (runs in executor)."""
        req = Request(url, data=data, headers=headers or {})
        try:
            resp = urlopen(req, timeout=timeout)
            body = resp.read()
            return resp.status, body, None
        except HTTPError as e:
            body = e.read() if hasattr(e, 'read') else b''
            return e.code, body, str(e)
        except Exception as e:
            return 0, b'', str(e)

    async def run_test(self, test: dict) -> TestResult:
        """Run a single test."""
        name = test.get("name", "unnamed")
        result = TestResult(name=name)

        # Custom handler
        if "handler" in test:
            try:
                r = await test["handler"]()
                result.status = "passed" if r else "failed"
                result.error = "" if r else "Handler returned falsy"
            except Exception as e:
                result.status = "failed"
                result.error = str(e)
            return result

        # Standard HTTP test
        endpoint = test.get("endpoint", "/")
        method = test.get("method", "GET")
        expected = test.get("expected_status", 200)
        result.endpoint = endpoint
        result.method = method
        result.expected_status = expected

        url = f"{self.base_url}{endpoint}"
        t0 = time.time()

        body = test.get("body")
        data = None
        if body:
            data = json.dumps(body).encode()

        status_code, resp_body, err = await self._request(
            method, url, data=data,
            headers={"Content-Type": "application/json",
                     **test.get("headers", {})},
            timeout=10,
        )

        result.actual_status = status_code
        result.latency_ms = (time.time() - t0) * 1000

        if err and not resp_body:
            result.status = "failed"
            result.error = err[:200]
        elif status_code == expected:
            result.status = "passed"
        else:
            result.status = "failed"
            result.error = f"Expected {expected}, got {status_code}"

        # Check JSON keys
        check_keys = test.get("check_json_keys")
        if check_keys and result.status == "passed":
            try:
                data = json.loads(resp_body)
                for key in check_keys:
                    if key not in data:
                        result.status = "failed"
                        result.error = f"Missing key '{key}' in response"
                        break
            except Exception:
                pass

        # Check HTML response
        if test.get("check_html") and result.status == "passed":
            if len(resp_body) < 50:
                result.status = "failed"
                result.error = f"Response too short ({len(resp_body)} bytes)"
            result.response_sample = str(resp_body[:100])

        return result

    async def run_suite(self, name: str = "auto", spec: Any = None,
                         fail_fast: bool = False) -> TestSuite:
        """Run all discovered tests."""
        suite = TestSuite(name=name)
        suite.started_at = time.time()
        tests = self.discover_endpoints(spec)

        VISIBILITY.action("autotest.start",
                          f"Running {len(tests)} tests ({name})")

        for test in tests:
            result = await self.run_test(test)
            suite.results.append(result)

            if result.status == "failed":
                VISIBILITY.log("ERROR", "autotest",
                               f"FAILED: {result.name}",
                               {"endpoint": result.endpoint,
                                "expected": result.expected_status,
                                "actual": result.actual_status,
                                "error": result.error})
                if fail_fast:
                    break
            elif result.status == "passed":
                VISIBILITY.log("DEBUG", "autotest",
                               f"PASSED: {result.name}",
                               {"latency_ms": result.latency_ms})

        suite.completed_at = time.time()

        # Summary
        summary = suite.summary()
        if summary["failed"] > 0:
            VISIBILITY.action("autotest.complete",
                              f"{summary['passed']}/{summary['total']} passed, "
                              f"{summary['failed']} FAILED",
                              {"summary": summary})
        else:
            VISIBILITY.action("autotest.complete",
                              f"{summary['passed']}/{summary['total']} passed",
                              {"summary": summary})

        self._suites.append(suite)
        return suite

    async def run_periodic(self, spec: Any = None, interval_s: float = 300):
        """Run tests periodically."""
        self._running = True
        while self._running:
            await self.run_suite("periodic", spec)
            await asyncio.sleep(interval_s)

    def stop(self):
        self._running = False

    def get_results(self, n: int = 5) -> list[TestSuite]:
        return self._suites[-n:]

    def get_failures(self) -> list[TestResult]:
        failures = []
        for suite in self._suites:
            for result in suite.results:
                if result.status == "failed":
                    failures.append(result)
        return failures

    def get_summary(self) -> dict:
        total = sum(len(s.results) for s in self._suites)
        failed = sum(len([r for r in s.results if r.status == "failed"])
                     for s in self._suites)
        return {
            "suites": len(self._suites),
            "total_tests": total,
            "total_failed": failed,
            "last_suite": self._suites[-1].summary() if self._suites else None,
            "failures": [{"name": r.name, "endpoint": r.endpoint,
                          "error": r.error} for r in self.get_failures()],
        }
