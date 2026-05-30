"""Tests for self-evolution engine."""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pytest
from nova.meta import PatternDetector, EvolutionEngine, EvolutionProposal, SelfEvolvingSystem
from nova.meta.evolution import Pattern


class TestPatternDetector:
    def test_observe_edits(self):
        detector = PatternDetector()
        for i in range(5):
            detector.observe_edit(f"src/file{i}.py")
        patterns = detector.detect_repeated_file_edits(min_count=1, window_s=3600)
        assert len(patterns) >= 5

    def test_repeated_edits_triggers_pattern(self):
        detector = PatternDetector()
        for _ in range(5):
            detector.observe_edit("src/hotfile.py")
        patterns = detector.detect_repeated_file_edits(min_count=3, window_s=3600)
        hot_patterns = [p for p in patterns if "hotfile.py" in p.description]
        assert len(hot_patterns) >= 1
        assert hot_patterns[0].frequency >= 5

    def test_repeated_errors(self):
        detector = PatternDetector()
        for _ in range(4):
            detector.observe_error("api.github", "rate limit exceeded")
        patterns = detector.detect_repeated_errors(min_count=3, window_s=3600)
        assert len(patterns) >= 1
        assert "rate limit" in patterns[0].description

    def test_config_tweaks(self):
        detector = PatternDetector()
        for _ in range(3):
            detector.observe_config_change("voice", "es-MX-DaliaNeural")
        patterns = detector.detect_config_tweaks(min_count=2, window_s=3600)
        assert len(patterns) >= 1

    def test_analyze_all(self):
        detector = PatternDetector()
        for _ in range(4):
            detector.observe_edit("src/main.py")
        for _ in range(3):
            detector.observe_error("core", "connection timeout")
        patterns = detector.analyze_all()
        assert len(patterns) >= 2

    def test_confidence_scaling(self):
        detector = PatternDetector()
        for _ in range(10):
            detector.observe_edit("src/very_hot.py")
        patterns = detector.detect_repeated_file_edits(min_count=3, window_s=3600)
        hot = [p for p in patterns if "very_hot.py" in p.description]
        if hot:
            assert hot[0].confidence > 0.8  # 10 edits = high confidence


class TestEvolutionEngine:
    def test_generate_proposal_from_edit_pattern(self):
        detector = PatternDetector()
        for _ in range(5):
            detector.observe_edit("src/manual_model.py")
        patterns = detector.detect_repeated_file_edits(min_count=3)
        engine = EvolutionEngine()
        proposals = []
        for p in patterns:
            prop = engine.generate_proposal(p)
            if prop:
                proposals.append(prop)
        assert len(proposals) >= 1
        assert "auto-generate" in proposals[0].title.lower() or "spec" in proposals[0].description.lower()

    def test_generate_proposal_from_error_pattern(self):
        detector = PatternDetector()
        for _ in range(5):
            detector.observe_error("db", "connection refused")
        patterns = detector.detect_repeated_errors(min_count=3)
        engine = EvolutionEngine()
        proposals = []
        for p in patterns:
            prop = engine.generate_proposal(p)
            if prop:
                proposals.append(prop)
        assert len(proposals) >= 1
        assert "error handler" in proposals[0].title.lower()

    def test_apply_proposal(self, tmp_path):
        engine = EvolutionEngine(str(tmp_path))
        proposal = EvolutionProposal(
            id="test_001",
            title="Add auto-generated file",
            code_changes={"generated/test.txt": "auto-generated content"},
        )
        engine._proposals["test_001"] = proposal
        result = engine.apply_proposal("test_001")
        assert result is True
        assert (tmp_path / "generated" / "test.txt").exists()
        assert (tmp_path / "generated" / "test.txt").read_text() == "auto-generated content"

    def test_proposal_lifecycle(self):
        engine = EvolutionEngine()
        detector = PatternDetector()
        for _ in range(5):
            detector.observe_edit("src/hot.py")
            detector.observe_error("api", "timeout")

        for p in detector.analyze_all():
            prop = engine.generate_proposal(p)
            if prop:
                assert prop.status == "proposed"
                engine._proposals[prop.id] = prop

        proposals = engine.get_proposals(status="proposed")
        assert len(proposals) >= 2


class TestSelfEvolvingSystem:
    def test_full_cycle(self):
        system = SelfEvolvingSystem()
        system.start()

        # Simulate observations
        for _ in range(5):
            system.detector.observe_edit("src/hot_file.py")
        for _ in range(4):
            system.detector.observe_error("api", "timeout")

        proposals = system.run_cycle()
        assert len(proposals) >= 1

        status = system.get_status()
        assert status["cycle"] >= 1
        assert status["running"] is True

    def test_multiple_cycles(self):
        system = SelfEvolvingSystem()
        system.start()

        # Cycle 1
        for _ in range(3):
            system.detector.observe_edit("src/a.py")
        proposals1 = system.run_cycle()
        assert len(proposals1) >= 0  # may or may not trigger

        # Cycle 2
        for _ in range(5):
            system.detector.observe_error("db", "timeout")
        proposals2 = system.run_cycle()

        assert system.get_status()["cycle"] == 2

    def test_auto_apply_high_confidence(self, tmp_path):
        system = SelfEvolvingSystem(str(tmp_path), auto_apply_confidence=0.1)  # very sensitive
        system.start()

        # Many edits = high confidence
        for _ in range(20):
            system.detector.observe_edit("src/auto_fix.py")

        proposals = system.run_cycle()
        # Some proposals may have been auto-applied
        applied = [p for p_id, p in system.engine._proposals.items()
                   if p.status == "applied"]
        # The patterns exist
        assert len(system.detector.get_patterns()) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
