# CASE: OCP violations — type-tag dispatch (OCP-1), closed conditional (OCP-2).
# DECOY: a match statement over a sealed StrEnum in a well-designed factory registry.
# The match is NOT a violation because new variants require both adding the enum member
# AND registering a handler — the extension point is register_shape(), not this match.
from __future__ import annotations

import math
from enum import StrEnum


class ShapeKind(StrEnum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"


# VIOLATION OCP-1: compute_area extends behaviour by an if/elif on a type tag.
# Adding a new shape requires editing this closed function body.
def compute_area(shape: dict) -> float:
    kind = shape.get("kind")
    if kind == "circle":
        radius = float(shape["radius"])
        return math.pi * radius * radius
    elif kind == "rectangle":
        return float(shape["width"]) * float(shape["height"])
    elif kind == "triangle":
        return 0.5 * float(shape["base"]) * float(shape["height"])
    else:
        raise ValueError(f"Unknown shape: {kind}")


# VIOLATION OCP-2: Renderer.render_shape is a closed conditional — adding a new
# output format requires editing this function rather than registering a new strategy.
class Renderer:
    def render_shape(self, shape: dict, fmt: str) -> str:
        if fmt == "svg":
            return f"<svg>{shape}</svg>"
        elif fmt == "ascii":
            return f"[ascii:{shape}]"
        elif fmt == "html":
            return f"<div>{shape}</div>"
        else:
            raise ValueError(f"Unsupported format: {fmt}")


# DECOY: correct OCP pattern — factory registry with sealed enum.
# Extension point is register_shape() and the enum definition, not the match.
# A naive reviewer may flag this as OCP-1 because it has a match on a type tag,
# but the match exhausts a sealed enum and the correct extension mechanism is external.
_SHAPE_REGISTRY: dict[ShapeKind, type] = {}


class BaseShape:
    kind: ShapeKind

    def area(self) -> float:
        raise NotImplementedError


class Circle(BaseShape):
    kind = ShapeKind.CIRCLE

    def __init__(self, radius: float) -> None:
        self.radius = radius

    def area(self) -> float:
        return math.pi * self.radius**2


class Rectangle(BaseShape):
    kind = ShapeKind.RECTANGLE

    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height


def register_shape(cls: type[BaseShape]) -> None:
    _SHAPE_REGISTRY[cls.kind] = cls


register_shape(Circle)
register_shape(Rectangle)


def create_shape(kind: ShapeKind, **kwargs: float) -> BaseShape:
    """Create a shape via the registry.

    DECOY: the match on ShapeKind is NOT an OCP-1 violation.  The sealed enum means
    no new variant can be added without touching the enum definition; the extension
    point is register_shape().
    """
    match kind:
        case ShapeKind.CIRCLE:
            return Circle(kwargs["radius"])
        case ShapeKind.RECTANGLE:
            return Rectangle(kwargs["width"], kwargs["height"])
        case ShapeKind.TRIANGLE:
            cls = _SHAPE_REGISTRY[kind]
            return cls(**kwargs)
