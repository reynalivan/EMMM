# app/models/game_model.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import uuid


@dataclass(frozen=True)
class Game:
    """Represents a single game configuration. Immutable."""

    name: str
    path: Path
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Post-initialization validation."""
        if not self.path.is_dir():
            raise ValueError(f"Game path must be an existing directory: {self.path}")
