"""Base dataclass for evaluation criteria."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Criterion:
    """A single evaluation criterion."""

    name: str
    description: str
    detection_hint: str
    weight: float  # relative weight within its dimension (0-1)
