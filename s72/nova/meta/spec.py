"""Spec Parser — reads app.yaml and produces structured Spec objects."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path


@dataclass
class FieldSpec:
    name: str
    type: str = "string"
    required: bool = False
    unique: bool = False
    default: Any = None
    description: str = ""


@dataclass
class RelationshipSpec:
    model: str = ""
    cardinality: str = "many-to-one"


@dataclass
class ModelSpec:
    name: str
    fields: list[FieldSpec] = field(default_factory=list)
    relationships: list[RelationshipSpec] = field(default_factory=list)
    table_name: str = ""


@dataclass
class RouteSpec:
    pattern: str
    methods: list[str] = field(default_factory=lambda: ["GET"])
    model: str = ""
    permissions: list[str] = field(default_factory=list)
    ai_powered: bool = False
    generator: bool = False
    description: str = ""


@dataclass
class SourceSpec:
    name: str
    type: str = "rest"
    endpoint: str = ""
    enabled: bool = True


@dataclass
class PipelineStageSpec:
    name: str
    action: str = ""
    using: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class PipelineSpec:
    name: str
    trigger: str = "on_demand"
    stages: list[PipelineStageSpec] = field(default_factory=list)


@dataclass
class AISpec:
    providers: dict = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)


@dataclass
class UISpec:
    layout: str = "feed"
    theme: str = "dark"
    components: list[str] = field(default_factory=list)


@dataclass
class Spec:
    """Application specification — drives code generation."""
    name: str = "app"
    version: str = "0.1.0"
    description: str = ""
    models: list[ModelSpec] = field(default_factory=list)
    routes: list[RouteSpec] = field(default_factory=list)
    sources: list[SourceSpec] = field(default_factory=list)
    pipelines: list[PipelineSpec] = field(default_factory=list)
    ai: AISpec = field(default_factory=AISpec)
    ui: UISpec = field(default_factory=UISpec)

    @classmethod
    def from_dict(cls, data: dict) -> "Spec":
        spec = cls(
            name=data.get("name", "app"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
        )
        # Parse models
        for m in data.get("models", []):
            fields = []
            for f_name, f_info in m.get("fields", {}).items():
                if isinstance(f_info, str):
                    fields.append(FieldSpec(name=f_name, type=f_info))
                elif isinstance(f_info, dict):
                    fields.append(FieldSpec(
                        name=f_name,
                        type=f_info.get("type", "string"),
                        required=f_info.get("required", False),
                        unique=f_info.get("unique", False),
                        default=f_info.get("default"),
                        description=f_info.get("description", ""),
                    ))
            relationships = []
            for rel in m.get("relationships", []):
                relationships.append(RelationshipSpec(
                    model=rel.get("model", ""),
                    cardinality=rel.get("cardinality", "many-to-one"),
                ))
            spec.models.append(ModelSpec(
                name=m["name"],
                fields=fields,
                relationships=relationships,
                table_name=m.get("table_name", m["name"].lower()),
            ))
        # Parse routes
        for r in data.get("routes", []):
            spec.routes.append(RouteSpec(
                pattern=r.get("pattern", "/"),
                methods=r.get("methods", ["GET"]),
                model=r.get("model", ""),
                permissions=r.get("permissions", []),
                ai_powered=r.get("ai_powered", False),
                generator=r.get("generator", False),
                description=r.get("description", ""),
            ))
        # Parse sources
        for s in data.get("sources", []):
            spec.sources.append(SourceSpec(
                name=s.get("name", ""),
                type=s.get("type", "rest"),
                endpoint=s.get("endpoint", ""),
                enabled=s.get("enabled", True),
            ))
        # Parse pipelines
        for p in data.get("pipelines", []):
            stages = [PipelineStageSpec(**s) for s in p.get("stages", [])]
            spec.pipelines.append(PipelineSpec(
                name=p.get("name", ""),
                trigger=p.get("trigger", "on_demand"),
                stages=stages,
            ))
        # Parse AI
        ai_data = data.get("ai", {})
        spec.ai = AISpec(
            providers=ai_data.get("providers", {}),
            capabilities=ai_data.get("capabilities", []),
        )
        # Parse UI
        ui_data = data.get("ui", {})
        spec.ui = UISpec(
            layout=ui_data.get("layout", "feed"),
            theme=ui_data.get("theme", "dark"),
            components=ui_data.get("components", []),
        )
        return spec


def parse_spec(path: str | Path) -> Spec:
    """Parse a YAML spec file into a Spec object."""
    import yaml
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Spec not found: {path}")
    data = yaml.safe_load(path.read_text())
    return Spec.from_dict(data)
