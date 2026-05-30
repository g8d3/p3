"""NOVA Meta-Layer — spec-driven code generation and self-building."""

from .spec import Spec, ModelSpec, FieldSpec, RouteSpec, PipelineSpec, parse_spec
from .codegen import CodeGenerator, ModelGenerator, RouteGenerator, UIGenerator, TestGenerator
from .watcher import SpecWatcher
from .evolution import PatternDetector, EvolutionEngine, EvolutionProposal, SelfEvolvingSystem

__all__ = [
    "Spec", "ModelSpec", "FieldSpec", "RouteSpec", "PipelineSpec", "parse_spec",
    "CodeGenerator", "ModelGenerator", "RouteGenerator", "UIGenerator", "TestGenerator",
    "SpecWatcher",
    "PatternDetector", "EvolutionEngine", "EvolutionProposal", "SelfEvolvingSystem",
]
