# app/models/mod_item_model.py

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import datetime
from typing import Optional, List


class ModType(Enum):
    CHARACTER = "Character"
    WEAPON = "Weapon"
    UI = "UI"
    OTHER = "Other"


class ModStatus(Enum):
    """Represents the enabled/disabled state of a mod."""

    ENABLED = auto()
    DISABLED = auto()


@dataclass(frozen=True)
class BaseModItem:
    """Base class for all mod items, containing common properties."""

    id: str
    actual_name: str
    folder_path: Path
    status: ModStatus
    is_pinned: bool
    # A flag to indicate if this is a skeleton object awaiting hydration.
    is_skeleton: bool = True


# --- ObjectList Models ---


@dataclass(frozen=True)
class ObjectItem(BaseModItem):
    """Represents a top-level mod category in the objectlist."""

    object_type: ModType | None = ModType.OTHER
    tags: list[str] = field(default_factory=list)
    release_date: datetime.date | None = None
    thumbnail_path: Path | None = None


@dataclass(frozen=True)
class CharacterObjectItem(ObjectItem):
    """Specific type for Characters, with detailed metadata."""

    gender: str | None = None
    rarity: str | None = None
    element: str | None = None
    weapon: str | None = None
    region: str | None = None


@dataclass(frozen=True)
class GenericObjectItem(ObjectItem):
    """Type for other categories (Weapon, NPC, etc.) with simple metadata."""

    subtype: str | None = None


# --- FolderGrid Model ---


@dataclass(frozen=True)
class FolderItem(BaseModItem):
    """Represents a single mod variant or a navigable folder in the foldergrid."""

    author: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    preview_images: List[Path] = field(default_factory=list)
    is_navigable: Optional[bool] = None
    is_safe: bool = False
    last_status_active: bool = True
    preset_name: Optional[str] = None


@dataclass(frozen=True)
class KeyBinding:
    key: str
    back: Optional[str] = None
    type: Optional[str] = None
    variable: Optional[str] = None
    default_value: Optional[str] = None
    options: List[str] = field(default_factory=list)
