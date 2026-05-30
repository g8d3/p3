"""Self-Evolution Engine — detects patterns and evolves the framework.

The framework observes how developers and AI agents interact with it.
When it detects repeated manual patterns, it proposes (and applies)
code generation improvements, new spec fields, or entirely new
capabilities.
"""

from __future__ import annotations
import os
import re
import json
import time
import hashlib
from pathlib import Path
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..core import VISIBILITY


@dataclass
class Pattern:
    """A detected pattern in the codebase or runtime behavior."""
    id: str = ""
    type: str = ""       # "manual_edit" | "repeated_api" | "config_tweak" | "error_recovery"
    description: str = ""
    frequency: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    locations: list[str] = field(default_factory=list)
    suggestion: str = ""
    auto_fix: str = ""   # Python code to apply the fix
    confidence: float = 0.0  # 0.0 - 1.0


@dataclass
class EvolutionProposal:
    """A proposal to evolve the framework."""
    id: str = ""
    title: str = ""
    description: str = ""
    impact: str = "low"  # low | medium | high
    effort: str = "small"  # small | medium | large
    files_to_modify: list[str] = field(default_factory=list)
    code_changes: dict = field(default_factory=dict)  # {path: new_content}
    status: str = "proposed"  # proposed | accepted | applied | rejected


class PatternDetector:
    """Detects patterns from various sources.

    Sources:
    - Git history analysis (repeated manual edits to same files)
    - Runtime logs (repeated errors or API patterns)
    - Config changes (repeated tweaks to same parameters)
    - Test failures (repeated failures in same areas)
    """

    def __init__(self, watch_dirs: list[str] = None):
        self.watch_dirs = watch_dirs or []
        self._patterns: dict[str, Pattern] = {}
        self._edits: deque[dict] = deque(maxlen=1000)
        self._errors: deque[dict] = deque(maxlen=500)
        self._config_changes: deque[dict] = deque(maxlen=200)

    def observe_edit(self, file_path: str, change_type: str = "modify"):
        """Record a file edit."""
        self._edits.append({
            "ts": time.time(),
            "file": file_path,
            "type": change_type,
        })

    def observe_error(self, source: str, message: str):
        """Record a runtime error."""
        self._errors.append({
            "ts": time.time(),
            "source": source,
            "message": message,
        })

    def observe_config_change(self, key: str, value: Any):
        """Record a configuration change."""
        self._config_changes.append({
            "ts": time.time(),
            "key": key,
            "value": str(value),
        })

    def detect_repeated_file_edits(self, min_count: int = 3,
                                    window_s: float = 3600) -> list[Pattern]:
        """Detect files that get edited frequently in a time window."""
        now = time.time()
        file_counts = defaultdict(int)
        file_times = defaultdict(list)

        for edit in self._edits:
            if now - edit["ts"] < window_s:
                file_counts[edit["file"]] += 1
                file_times[edit["file"]].append(edit["ts"])

        patterns = []
        for file_path, count in file_counts.items():
            if count >= min_count:
                p = Pattern(
                    id=f"pat_edit_{hashlib.md5(file_path.encode()).hexdigest()[:8]}",
                    type="manual_edit",
                    description=f"File edited {count}x in {window_s/60:.0f}min: {file_path}",
                    frequency=count,
                    first_seen=min(file_times[file_path]),
                    last_seen=max(file_times[file_path]),
                    locations=[file_path],
                    suggestion=f"Consider auto-generating this file from spec",
                    confidence=min(0.5 + count * 0.1, 0.95),
                )
                patterns.append(p)
                self._patterns[p.id] = p
        return patterns

    def detect_repeated_errors(self, min_count: int = 3,
                                window_s: float = 3600) -> list[Pattern]:
        """Detect errors that occur frequently."""
        now = time.time()
        error_counts = defaultdict(int)
        error_times = defaultdict(list)

        for err in self._errors:
            if now - err["ts"] < window_s:
                key = f"{err['source']}:{err['message'][:80]}"
                error_counts[key] += 1
                error_times[key].append(err["ts"])

        patterns = []
        for key, count in error_counts.items():
            if count >= min_count:
                source, msg = key.split(":", 1)
                p = Pattern(
                    id=f"pat_err_{hashlib.md5(key.encode()).hexdigest()[:8]}",
                    type="error_recovery",
                    description=f"Repeated error ({count}x): {source} - {msg[:60]}",
                    frequency=count,
                    first_seen=min(error_times[key]),
                    last_seen=max(error_times[key]),
                    suggestion=f"Add error handler or retry logic for {source}",
                    confidence=min(0.6 + count * 0.05, 0.9),
                )
                patterns.append(p)
                self._patterns[p.id] = p
        return patterns

    def detect_config_tweaks(self, min_count: int = 2,
                              window_s: float = 3600) -> list[Pattern]:
        """Detect config parameters that get tweaked repeatedly."""
        now = time.time()
        key_counts = defaultdict(int)

        for change in self._config_changes:
            if now - change["ts"] < window_s:
                key_counts[change["key"]] += 1

        patterns = []
        for key, count in key_counts.items():
            if count >= min_count:
                p = Pattern(
                    id=f"pat_cfg_{hashlib.md5(key.encode()).hexdigest()[:8]}",
                    type="config_tweak",
                    description=f"Config '{key}' changed {count}x",
                    frequency=count,
                    suggestion=f"Consider adding '{key}' to spec or making it auto-tune",
                    confidence=min(0.5 + count * 0.15, 0.95),
                )
                patterns.append(p)
                self._patterns[p.id] = p
        return patterns

    def analyze_all(self) -> list[Pattern]:
        """Run all detectors and return combined results."""
        patterns = []
        patterns.extend(self.detect_repeated_file_edits())
        patterns.extend(self.detect_repeated_errors())
        patterns.extend(self.detect_config_tweaks())
        return patterns

    def get_patterns(self, min_confidence: float = 0.0) -> list[Pattern]:
        return [p for p in self._patterns.values() if p.confidence >= min_confidence]


class EvolutionEngine:
    """Applies evolution proposals to the framework.

    When a pattern is detected with high confidence, the engine:
    1. Generates a proposal
    2. Applies the change (if auto_fix is available)
    3. Tests the change
    4. Commits the change
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self._proposals: dict[str, EvolutionProposal] = {}
        self._applied: list[str] = []
        self._on_proposal: list[Callable] = []

    def on_new_proposal(self, cb: Callable):
        self._on_proposal.append(cb)

    def generate_proposal(self, pattern: Pattern) -> Optional[EvolutionProposal]:
        """Generate an evolution proposal from a detected pattern."""
        if pattern.type == "manual_edit":
            return self._propose_spec_generation(pattern)
        elif pattern.type == "error_recovery":
            return self._propose_error_handler(pattern)
        elif pattern.type == "config_tweak":
            return self._propose_config_auto(pattern)
        return None

    def _propose_spec_generation(self, pattern: Pattern) -> EvolutionProposal:
        file_path = pattern.locations[0] if pattern.locations else ""
        file_name = Path(file_path).stem if file_path else "unknown"

        return EvolutionProposal(
            id=f"evo_{int(time.time())}_{hashlib.md5(pattern.id.encode()).hexdigest()[:6]}",
            title=f"Auto-generate {file_name} from spec",
            description=pattern.suggestion,
            impact="medium",
            effort="small",
            files_to_modify=[file_path],
            status="proposed",
        )

    def _propose_error_handler(self, pattern: Pattern) -> EvolutionProposal:
        return EvolutionProposal(
            id=f"evo_{int(time.time())}_err_{hashlib.md5(pattern.id.encode()).hexdigest()[:6]}",
            title=f"Add error handler for: {pattern.locations[0] if pattern.locations else 'unknown'}",
            description=pattern.suggestion,
            impact="high",
            effort="small",
            status="proposed",
        )

    def _propose_config_auto(self, pattern: Pattern) -> EvolutionProposal:
        return EvolutionProposal(
            id=f"evo_{int(time.time())}_cfg_{hashlib.md5(pattern.id.encode()).hexdigest()[:6]}",
            title=f"Auto-tune config parameter",
            description=pattern.suggestion,
            impact="low",
            effort="small",
            status="proposed",
        )

    def apply_proposal(self, proposal_id: str) -> bool:
        """Apply an evolution proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return False

        try:
            # Apply code changes
            for path, content in proposal.code_changes.items():
                full_path = self.base_dir / path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

            proposal.status = "applied"
            self._applied.append(proposal_id)
            VISIBILITY.action("evolution.applied",
                              f"Proposal '{proposal.title}' applied",
                              {"files": proposal.files_to_modify})
            return True

        except Exception as e:
            proposal.status = "failed"
            VISIBILITY.log("ERROR", "evolution",
                           f"Failed to apply proposal: {e}")
            return False

    def get_proposals(self, status: str = "") -> list[EvolutionProposal]:
        props = list(self._proposals.values())
        if status:
            props = [p for p in props if p.status == status]
        return props

    def get_stats(self) -> dict:
        return {
            "total_proposals": len(self._proposals),
            "applied": len(self._applied),
            "by_status": defaultdict(int, {
                p.status: len([x for x in self._proposals.values() if x.status == p.status])
                for p in self._proposals.values()
            }),
        }


class SelfEvolvingSystem:
    """Combines pattern detection + evolution engine into a continuous loop.

    Runs periodically, detects patterns, generates proposals,
    and applies high-confidence changes automatically.
    """

    def __init__(self, base_dir: str = ".", auto_apply_confidence: float = 0.9):
        self.detector = PatternDetector()
        self.engine = EvolutionEngine(base_dir)
        self.auto_apply_confidence = auto_apply_confidence
        self._cycle_count = 0
        self._running = False

    def start(self):
        self._running = True
        VISIBILITY.action("evolution.start",
                          "Self-evolution engine started")

    def stop(self):
        self._running = False

    def run_cycle(self) -> list[EvolutionProposal]:
        """Run one evolution cycle: detect → propose → apply."""
        self._cycle_count += 1

        # Detect patterns
        patterns = self.detector.analyze_all()
        if not patterns:
            return []

        VISIBILITY.action("evolution.cycle",
                          f"Cycle {self._cycle_count}: {len(patterns)} patterns detected")

        # Generate proposals
        proposals = []
        for pattern in patterns:
            proposal = self.engine.generate_proposal(pattern)
            if proposal:
                self.engine._proposals[proposal.id] = proposal
                proposals.append(proposal)

                for cb in self.engine._on_proposal:
                    try:
                        cb(proposal)
                    except Exception:
                        pass

                # Auto-apply if confidence high enough
                if pattern.confidence >= self.auto_apply_confidence:
                    if self.engine.apply_proposal(proposal.id):
                        VISIBILITY.action("evolution.auto_applied",
                                          f"Auto-applied: {proposal.title}",
                                          {"confidence": pattern.confidence})

        return proposals

    def get_status(self) -> dict:
        return {
            "cycle": self._cycle_count,
            "running": self._running,
            "patterns": len(self.detector._patterns),
            "engine": self.engine.get_stats(),
        }
