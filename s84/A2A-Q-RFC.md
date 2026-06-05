# A2A-Q: Quality Extension for the Agent-to-Agent Protocol

> **Status**: Draft Proposal v0.1
> **Extension ID**: `a2a-quality`
> **Protocol Version**: A2A 1.0+
> **Author**: Community proposal
> **Date**: 2026-06-05
> **Repository**: https://github.com/a2aproject/A2A (proposed)

---

## 1. Motivation

### 1.1 The Quality Gap in A2A

The A2A Protocol v1.0 defines how agents discover, communicate, and delegate
tasks. Its design principle of **opaque execution** — agents collaborate without
sharing internal state, reasoning, or tools — is appropriate for interoperability.

However, this opacity creates a **quality gap**. When agent A delegates a task
to agent B:

```
Agent A                    Agent B
   │                          │
   │  POST /message:send      │
   │─────────────────────────▶│
   │                          │  (does work)
   │  GET /tasks/{id}         │
   │◀─────────────────────────│
   │  status.state =           │
   │  "completed"              │  ← Same state regardless of quality
```

A2A's `TaskState` has no distinction between:
- **"completed successfully"** (all criteria met)
- **"completed with issues"** (work done but quality checks failed)
- **"needs revision"** (work done, reviewed, and sent back)

Quality information, when it exists, is buried in artifact text — invisible to
the protocol, to orchestrators, and to audit systems.

### 1.2 Efficacy & Efficiency Are Missing

Beyond pass/fail quality, there is no standardized way to track:
- **Efficacy**: How well did the agent perform? (quality score, criteria pass rate)
- **Efficiency**: How fast and cheap was the work? (wall time, tokens, cycles)
- **Process quality**: Was the right agent chosen? Where was the bottleneck?

Without these, agent selection is blind: an orchestrator cannot distinguish a
fast, accurate agent from a slow, error-prone one.

### 1.3 Scope

This extension addresses the **quality layer** — the gap between "task completed"
and "task completed correctly." It does NOT address:
- Transport, security, or discovery (handled by A2A base)
- Agent supervision, crash recovery, or health checks
- Autonomous work cycle scheduling

---

## 2. Extension Declaration

### 2.1 Agent Card Extension

Agents supporting A2A-Q declare it in their Agent Card:

```json
{
  "extensions": [
    {
      "id": "a2a-quality",
      "version": "0.1.0",
      "config": {
        "min_reviewers": 1,
        "auto_approve_skills": ["code-review", "validate", "quality-check"],
        "criteria": [
          "No syntax errors",
          "No hardcoded secrets",
          "Tests pass"
        ]
      }
    }
  ]
}
```

### 2.2 Protocol Header

Clients and servers signal A2A-Q support via the `A2A-Extensions` header
(as defined in A2A v1.0 Section 14.2.2):

```
A2A-Extensions: a2a-quality@0.1.0
```

Servers that do not support the extension MUST ignore the header.
Clients that receive operations or metadata they do not understand
MUST ignore unknown fields (per A2A v1.0 Section 5.7).

---

## 3. Extended Task State Machine

### 3.1 New States

A2A-Q defines four new `TaskState` values:

| State | Value | Description | Terminal? |
|-------|-------|-------------|-----------|
| **Pending Review** | `quality:pending-review` | Work is complete, waiting for validation | No |
| **Needs Revision** | `quality:needs-revision` | Checker rejected; agent must correct | No |
| **Quality Passed** | `quality:passed` | All quality gates passed | Yes |
| **Escalated** | `quality:escalated` | Quality ambiguous; human needed | Yes |

### 3.2 Full Extended State Machine

```
                  ┌──────────┐
                  │ submitted │
                  └────┬─────┘
                       │
                  ┌────▼─────┐
         ┌───────│  working  │◀────────────┐
         │       └────┬─────┘              │
         │            │ task complete      │
         │       ┌────▼──────────┐         │
         │       │quality:       │         │
         │       │pending-review │         │
         │       └────┬──────────┘         │
         │            │                    │
         │      ┌─────┴──────┐            │
         │      │            │             │
         │  ┌───▼──┐   ┌────▼──────┐     │
         │  │quality│   │ quality:  │     │
         │  │:passed│   │needs-     │─────┘
         │  └───────┘   │revision   │
         │              └───────────┘
         │
    ┌────▼─────────┐
    │  completed   │  (A2A base — terminal by default,
    └──────────────┘   but extended agents use quality:passed)
```

### 3.3 Transition Rules

| From | To | Trigger | Authority |
|------|----|---------|-----------|
| `working` | `quality:pending-review` | Work submitted for review | Agent (maker) |
| `quality:pending-review` | `quality:passed` | All criteria met | Checker |
| `quality:pending-review` | `quality:needs-revision` | Criteria not fully met | Checker |
| `quality:pending-review` | `quality:escalated` | Ambiguous or needs human | Checker |
| `quality:needs-revision` | `working` | Agent incorporates feedback | Agent (maker) |
| `quality:needs-revision` | `quality:escalated` | Repeated failures | Checker/Supervisor |
| `quality:passed` | → `completed` | (auto-transition to A2A terminal) | Protocol |

---

## 4. Quality Criteria

### 4.1 Skill-Level Criteria

Agents declare quality expectations per skill in their Agent Card:

```json
{
  "skills": [{
    "id": "code-review",
    "name": "Code Review",
    "qualityCriteria": {
      "version": "0.1.0",
      "autoFail": ["leaked_secret", "syntax_error", "api_key"],
      "checks": [
        {"id": "syntax", "description": "Syntactic correctness", "command": "node --check {file}"},
        {"id": "no-todos", "description": "No TODOs introduced", "type": "grep"},
        {"id": "tests", "description": "All tests pass", "command": "npm test"},
        {"id": "no-debug", "description": "No console.log debugging artifacts", "type": "grep"}
      ],
      "requiredReviewers": ["checker"],
      "minApprovals": 1
    }
  }]
}
```

### 4.2 Task-Level Criteria

Criteria can also be specified per-task, overriding or extending the skill defaults:

```json
{
  "metadata": {
    "a2a-quality:criteria": {
      "checks": [
        {"id": "response-time", "description": "Response under 5s", "max_ms": 5000},
        {"id": "format", "description": "JSON output", "schema": "..."}
      ],
      "min_score": 0.8
    }
  }
}
```

---

## 5. New Operations

### 5.1 POST /tasks/{id}:requestReview

Submit a completed task for quality review.

**Request**:
```json
{
  "reviewer": "checker | agent-id",
  "traceId": "trace-abc-123",
  "timeout": 120
}
```

**Behavior**:
1. Transitions task from `working` → `quality:pending-review`
2. The reviewer agent (or human) is notified
3. If `timeout` expires, task auto-transitions to `quality:escalated`

**Errors**:
- `TaskNotInWorkingState`: task is not in `working` state
- `ReviewerNotFound`: the reviewer agent card is not reachable
- `ReviewAlreadyRequested`: task is already in `quality:pending-review`

### 5.2 POST /tasks/{id}:submitVerdict

Submit a quality verdict for a task under review.

**Request**:
```json
{
  "decision": "approved | rejected | needs-work | escalated",
  "summary": "Validation passed. All criteria met.",
  "score": 0.95,
  "details": [
    {"check": "syntax", "pass": true, "detail": "node --check passed"},
    {"check": "no-todos", "pass": true},
    {"check": "tests", "pass": false, "detail": "2 tests failed",
     "severity": "error", "evidence": "test-output.log"}
  ],
  "traceId": "trace-abc-123"
}
```

**Behavior**:
| Decision | New State |
|----------|-----------|
| `approved` | `quality:passed` |
| `rejected` / `needs-work` | `quality:needs-revision` |
| `escalated` | `quality:escalated` |

**Errors**:
- `TaskNotInReview`: task is not in `quality:pending-review` state
- `InvalidDecision`: decision value not recognized

### 5.3 POST /tasks/{id}:requestRevision

Notify the orchestrator that the agent has completed a revision cycle and
the work is ready for re-review.

**Request**:
```json
{
  "traceId": "trace-abc-123",
  "changes": ["Fixed API key leak", "Added input validation"],
  "revision_count": 2
}
```

**Behavior**: Transitions from `quality:needs-revision` → `quality:pending-review`.

### 5.4 GET /tasks/{id}/quality

Retrieve the full quality report for a completed task.

**Response**:
```json
{
  "task_id": "task-abc-123",
  "final_state": "quality:passed",
  "efficacy": {
    "quality_score": 0.85,
    "pass": true,
    "revision_count": 2,
    "criteria_results": [
      {"check": "No syntax errors", "pass": true},
      {"check": "Tests pass", "pass": true},
      {"check": "No hardcoded secrets", "pass": false, "severity": "critical"}
    ]
  },
  "efficiency": {
    "total_wall_time_ms": 45000,
    "processing_time_ms": 12000,
    "review_time_ms": 33000,
    "revision_cycles": 2,
    "estimated_tokens": 45000,
    "tool_calls": 12,
    "utilization": 0.65
  },
  "process": {
    "assignment_correctness": "correct",
    "agent_selection_latency_ms": 200,
    "handoff_count": 0,
    "bottleneck": "review (66% of wall time)"
  }
}
```

---

## 6. Efficacy & Efficiency Metrics

### 6.1 Data Model

All metrics are stored in `Task.metadata` under reserved keys:

| Metadata Key | Type | Description |
|---|---|---|
| `a2a-quality:efficacy` | object | Quality score, pass/fail, criteria breakdown |
| `a2a-quality:efficiency` | object | Timing, token usage, utilization |
| `a2a-quality:hardware` | object | CPU, RAM, context window, network I/O |
| `a2a-quality:runtime` | object | Language, memory footprint, startup time |
| `a2a-quality:process` | object | Assignment quality, bottlenecks |
| `a2a-quality:trace` | array | Ordered history of quality hops |
| `a2a-quality:criteria` | object | Task-specific quality criteria |

### 6.2 Efficacy Metrics

```json
{
  "a2a-quality:efficacy": {
    "quality_score": 0.85,
    "pass": true,
    "revision_count": 2,
    "checker_verdicts": ["rejected", "rejected", "approved"],
    "criteria_results": [
      {"check": "syntax", "pass": true, "weight": 0.3},
      {"check": "tests", "pass": true, "weight": 0.4},
      {"check": "secrets", "pass": false, "weight": 0.3, "severity": "critical"}
    ]
  }
}
```

**Fields**:
- `quality_score`: Weighted average of criteria results (0.0–1.0). Calculated as
  `sum(pass * weight) / sum(weight)`.
- `pass`: `true` if `quality_score >= min_score` (default 0.7) AND no `autoFail`
  criteria failed.
- `revision_count`: Number of `quality:needs-revision` cycles.
- `checker_verdicts`: Ordered list of verdicts from checker(s).
- `criteria_results`: Individual check results. Each `check` maps to a criteria
  defined in the Agent Card or task-level criteria.

### 6.3 Efficiency Metrics

```json
{
  "a2a-quality:efficiency": {
    "total_wall_time_ms": 45000,
    "processing_time_ms": 12000,
    "review_time_ms": 33000,
    "revision_cycles": 2,
    "estimated_tokens": 45000,
    "tool_calls": 12,
    "utilization": 0.65
  }
}
```

**Fields**:
- `total_wall_time_ms`: Real elapsed time from task creation to terminal state.
- `processing_time_ms`: Time the agent spent actively working (excludes review).
- `review_time_ms`: Time the checker(s) spent reviewing.
- `revision_cycles`: Same as `revision_count` in efficacy (cross-reference).
- `estimated_tokens`: Approximate total tokens consumed (LLM input + output).
- `tool_calls`: Number of tool invocations during processing.
- `utilization`: `processing_time_ms / total_wall_time_ms`. Values near 1.0
  indicate high efficiency; values near 0.0 indicate time spent waiting.

### 6.3a Hardware & Runtime Metrics

```json
{
  "a2a-quality:hardware": {
    "local": {
      "cpu_usage_pct": 45.2,
      "memory_mb": 198,
      "context_size_tokens": 32000,
      "context_window_pct": 0.62,
      "process_count": 3
    },
    "remote": {
      "api_latency_ms": 340,
      "remote_gpu_used": "NVIDIA A10G (24GB)",
      "network_io_bytes": 245000
    }
  },
  "a2a-quality:runtime": {
    "language": "typescript",
    "runtime_memory_mb": 198,
    "startup_time_ms": 1200,
    "agent_type": "opencode | crush | claude-code | custom",
    "notes": "OpenCode ~200MB RAM (TypeScript), Crush ~30MB RAM (Go)"
  }
}
```

**Local hardware fields**:
- `cpu_usage_pct`: Average CPU utilization during task processing.
- `memory_mb`: Resident memory of the agent process (RSS). Useful for comparing
  runtime efficiency — e.g., TypeScript agents (OpenCode ~200MB) vs Go agents
  (Crush ~30MB).
- `context_size_tokens`: Total size of the context sent to the LLM.
- `context_window_pct`: Percentage of the LLM's context window consumed.
  Critical metric: high values indicate context pressure, risk of truncation.
- `process_count`: Number of child/spawned processes.

**Remote hardware fields**:
- `api_latency_ms`: Round-trip latency to external API calls.
- `remote_gpu_used`: GPU model and VRAM if cloud compute is used.
- `network_io_bytes`: Total bytes sent/received over the network.

**Runtime fields**:
- `language`: The agent's implementation language (Python, Go, TS, Rust...).
- `runtime_memory_mb`: Base memory footprint of the agent runtime.
- `startup_time_ms`: Cold-start time for the agent.
- `agent_type`: Categorizes the agent (opencode, crush, claude-code, custom).
- `notes`: Free-text for comparative observations.

### 6.4 Process Metrics

```json
{
  "a2a-quality:process": {
    "assignment_correctness": "correct | incorrect | partial",
    "agent_selection_latency_ms": 200,
    "handoff_count": 0,
    "context_retrieval_time_ms": 15,
    "bottleneck": "processing | review | context | assignment"
  }
}
```

**Fields**:
- `assignment_correctness`: Was the task assigned to the optimal agent?
  Set by the orchestrator after task completion.
- `agent_selection_latency_ms`: Time taken to select the target agent.
- `handoff_count`: Number of agent-to-agent handoffs during this task.
- `context_retrieval_time_ms`: Time to load context (session history, files).
- `bottleneck`: Where the most wall time was spent. Calculated from efficiency
  metrics: `max(processing_time_ms, review_time_ms, ...)`.

### 6.5 Quality Trace

```json
{
  "a2a-quality:trace": [
    {
      "from": "maker-A",
      "to": "checker-B",
      "state": "quality:pending-review",
      "ts": 1749060000,
      "duration_ms": 12000
    },
    {
      "from": "checker-B",
      "to": "maker-A",
      "state": "quality:needs-revision",
      "ts": 1749060100,
      "reason": "Hardcoded API key in config.js",
      "duration_ms": 500
    },
    {
      "from": "maker-A",
      "to": "checker-B",
      "state": "quality:pending-review",
      "ts": 1749060200,
      "duration_ms": 5000
    },
    {
      "from": "checker-B",
      "to": "",
      "state": "quality:passed",
      "ts": 1749060300,
      "duration_ms": 300
    }
  ]
}
```

---

## 7. Interoperability

### 7.1 Backward Compatibility

A2A-Q is fully backward compatible with A2A v1.0:

1. **Unknown fields**: A2A v1.0 Section 5.7 requires clients to ignore unknown
   fields. New metadata keys (`a2a-quality:*`) are safely ignored by
   non-participating agents.
2. **Unknown states**: Agents that receive `quality:passed` as a task state
   but don't support the extension will see it as an unrecognized state.
   They SHOULD treat unrecognized terminal states as equivalent to `completed`.
3. **Extension header**: The `A2A-Extensions` header is already defined in
   A2A v1.0 Section 14.2.2. Non-participating servers ignore it.

### 7.2 Graceful Degradation

If an agent declares A2A-Q support but a peer does not:

- Quality operations (`requestReview`, `submitVerdict`) return
  `UnsupportedOperationError` (standard A2A error).
- The requesting agent falls back to A2A base behavior: task completes
  directly with no quality gate.
- Quality metadata is still written to the task (visible in GET /tasks/{id}),
  even if the peer ignores it.

### 7.3 Extension Versioning

Per A2A v1.0 Section 4.6.3, extensions use semantic versioning:

- **Major**: Breaking changes to the quality state machine or required fields.
- **Minor**: New optional metrics, new optional criteria types.
- **Patch**: Clarifications, additional examples.

The `A2A-Extensions` header uses the format `a2a-quality@0.1.0`.

---

## 8. Security Considerations

### 8.1 Verdict Integrity

Quality verdicts affect agent reputation and task outcomes. Implementations
SHOULD:

- Sign verdicts with the checker's credentials (use Agent Card signatures
  per A2A v1.0 Section 8.4).
- Reject unsigned or mismatched verdicts in high-trust environments.

### 8.2 Score Manipulation

An agent SHOULD NOT self-validate its own work. The `requiredReviewers` field
in `qualityCriteria` MUST exclude the task's own agent.

### 8.3 Metric Forging

Efficacy and efficiency metrics are best-effort and self-reported.
In untrusted environments, metrics SHOULD be verified by a trusted
third party (orchestrator or audit service).

---

## 9. Examples

### 9.1 Simple Quality Flow

```
Client                  Maker Agent               Checker Agent
  │                         │                         │
  │  POST /message:send     │                         │
  │────────────────────────▶│                         │
  │  status: working        │                         │
  │◀────────────────────────│                         │
  │                         │  (does work)            │
  │                         │                         │
  │  POST /tasks/{id}:      │                         │
  │  requestReview          │                         │
  │────────────────────────▶│                         │
  │  status: pending-review │                         │
  │◀────────────────────────│                         │
  │                         │  POST /tasks/{id}:      │
  │                         │  submitVerdict          │
  │                         │  (by checker)           │
  │                         │◀────────────────────────│
  │                         │  decision: "approved"   │
  │                         │                         │
  │  GET /tasks/{id}        │                         │
  │────────────────────────▶│                         │
  │  status: quality:passed │                         │
  │  + efficacy/efficiency  │                         │
  │◀────────────────────────│                         │
```

### 9.2 Revision Cycle

```
  status: pending-review → needs-revision → pending-review → passed

  checker: "API key is hardcoded. Fix it."
  maker:   "Moved API key to env var. Ready for re-review."
  checker: "Approved."
  status:  quality:passed
  metrics: revision_count=1, checker_verdicts=["rejected","approved"]
```

### 9.3 Agent Comparison

After 100 tasks, an orchestrator can rank agents:

```
Agent           Avg Score   Avg Time   Rev/Cycle   Utilization
──────────────────────────────────────────────────────────────
maker-A         0.92        12s        0.3          0.78
maker-B         0.75        45s        2.1          0.45
maker-C         0.88        18s        0.7          0.62
```

→ maker-B is slow AND low quality. Consider retraining or replacing.
→ maker-A is the most efficient. Route high-priority tasks there.

---

## 10. Relationship to AOP

This extension is a subset of the **Agent Orchestration Protocol (AOP)** —
a broader specification for multi-agent orchestration with quality supervision.

AOP includes everything in A2A-Q plus:

| Feature | In A2A-Q? | In AOP? |
|---------|:---------:|:-------:|
| Quality gates | ✅ | ✅ |
| Efficacy metrics | ✅ | ✅ |
| Efficiency metrics | ✅ | ✅ |
| Transport (file bus) | ❌ (A2A HTTP) | ✅ |
| Supervisor (health checks) | ❌ | ✅ |
| Autonomous cycle (ciclador) | ❌ | ✅ |
| State machine (8 states) | ✅ (4 new states) | ✅ (4 states) |
| Trace hops | ✅ | ✅ (trace-helper) |
| Session context (HANDOFF.md) | ❌ | ✅ |

A2A-Q is the **interoperable subset** of AOP — the part that can become a
standard extension to A2A, benefiting the entire ecosystem rather than just
your deployment.

---

## 11. Implementation Roadmap

| Phase | Scope | Timeline |
|-------|-------|----------|
| **P0** | RFC published as GitHub Discussion on a2aproject/A2A | Week 1 |
| **P1** | Python reference implementation on `a2a-sdk` | Week 2-3 |
| **P2** | Test with real A2A agents (ADK, LangGraph, CrewAI) | Week 3-4 |
| **P3** | Iterate based on community feedback | Week 4-6 |
| **P4** | Submit as formal extension PR to A2A spec repo | Week 6 |

### P1 — Python Implementation Plan

```python
# a2a_quality/extension.py
from a2a.types import Task, AgentCard, Extension

class QualityExtension:
    """A2A-Q extension for a2a-sdk based agents."""
    
    def extend_agent_card(self, card: AgentCard) -> AgentCard:
        """Add a2a-quality extension declaration to an AgentCard."""
        card.extensions.append(Extension(
            id="a2a-quality",
            version="0.1.0"
        ))
        return card
    
    def request_review(self, task_id: str, reviewer: str) -> Task:
        """POST /tasks/{id}:requestReview"""
        ...
    
    def submit_verdict(self, task_id: str, verdict: dict) -> Task:
        """POST /tasks/{id}:submitVerdict"""
        ...
    
    def get_quality_report(self, task_id: str) -> dict:
        """GET /tasks/{id}/quality"""
        ...
```

---

## Appendix A. Changes to A2A Protocol Specification

If accepted, these sections of the A2A v1.0 spec would need modification:

| Section | Change |
|---------|--------|
| 4.1.3 TaskState | Add 4 new enum values: `quality:pending-review`, `quality:needs-revision`, `quality:passed`, `quality:escalated` |
| 4.1.2 TaskStatus | Add optional `score` field (0.0–1.0) |
| 4.4.5 AgentSkill | Add optional `qualityCriteria` field |
| 4.6.1 Extension Declaration | Add `a2a-quality` as registered extension |
| 3.1.x (new) | Add `RequestReview`, `SubmitVerdict`, `RequestRevision` operations |
| 5.3 Method Mapping | Add REST endpoints and JSON-RPC methods for new operations |
| 14.2.2 A2A-Extensions | Add `a2a-quality@0.1.0` to registered extension identifiers |

---

## Appendix B. Full JSON Schema for Extension Metadata

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "A2A-Q Extension Metadata",
  "type": "object",
  "properties": {
    "a2a-quality:efficacy": {
      "type": "object",
      "properties": {
        "quality_score": {"type": "number", "minimum": 0, "maximum": 1},
        "pass": {"type": "boolean"},
        "revision_count": {"type": "integer", "minimum": 0},
        "checker_verdicts": {"type": "array", "items": {"type": "string"}},
        "criteria_results": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "check": {"type": "string"},
              "pass": {"type": "boolean"},
              "weight": {"type": "number", "minimum": 0, "maximum": 1},
              "severity": {"type": "string", "enum": ["info", "warning", "error", "critical"]},
              "detail": {"type": "string"},
              "evidence": {"type": "string"}
            },
            "required": ["check", "pass"]
          }
        }
      },
      "required": ["quality_score", "pass"]
    },
    "a2a-quality:efficiency": {
      "type": "object",
      "properties": {
        "total_wall_time_ms": {"type": "integer", "minimum": 0},
        "processing_time_ms": {"type": "integer", "minimum": 0},
        "review_time_ms": {"type": "integer", "minimum": 0},
        "revision_cycles": {"type": "integer", "minimum": 0},
        "estimated_tokens": {"type": "integer", "minimum": 0},
        "tool_calls": {"type": "integer", "minimum": 0},
        "utilization": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "a2a-quality:process": {
      "type": "object",
      "properties": {
        "assignment_correctness": {"type": "string", "enum": ["correct", "incorrect", "partial"]},
        "agent_selection_latency_ms": {"type": "integer", "minimum": 0},
        "handoff_count": {"type": "integer", "minimum": 0},
        "context_retrieval_time_ms": {"type": "integer", "minimum": 0},
        "bottleneck": {"type": "string"}
      }
    },
    "a2a-quality:trace": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "from": {"type": "string"},
          "to": {"type": "string"},
          "state": {"type": "string"},
          "ts": {"type": "integer"},
          "duration_ms": {"type": "integer"},
          "reason": {"type": "string"}
        },
        "required": ["from", "to", "state", "ts"]
      }
    },
    "a2a-quality:hardware": {
      "type": "object",
      "properties": {
        "local": {
          "type": "object",
          "properties": {
            "cpu_usage_pct": {"type": "number"},
            "memory_mb": {"type": "number"},
            "context_size_tokens": {"type": "integer"},
            "context_window_pct": {"type": "number"},
            "process_count": {"type": "integer"}
          }
        },
        "remote": {
          "type": "object",
          "properties": {
            "api_latency_ms": {"type": "number"},
            "remote_gpu_used": {"type": "string"},
            "network_io_bytes": {"type": "integer"}
          }
        }
      }
    },
    "a2a-quality:runtime": {
      "type": "object",
      "properties": {
        "language": {"type": "string"},
        "runtime_memory_mb": {"type": "number"},
        "startup_time_ms": {"type": "integer"},
        "agent_type": {"type": "string"}
      }
    },
    "a2a-quality:criteria": {
      "type": "object",
      "properties": {
        "checks": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id": {"type": "string"},
              "description": {"type": "string"},
              "command": {"type": "string"},
              "max_ms": {"type": "integer"},
              "schema": {"type": "string"}
            },
            "required": ["id", "description"]
          }
        },
        "min_score": {"type": "number", "minimum": 0, "maximum": 1},
        "autoFail": {"type": "array", "items": {"type": "string"}}
      }
    }
  }
}
```

---

*This RFC is a living document. Feedback, implementation experience, and
edge cases will inform future revisions.*
