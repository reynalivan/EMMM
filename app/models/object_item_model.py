# app/models/object_item_model.py

from dataclasses import dataclass
from typing import Optional
from app.core.constants import DISABLED_PREFIX


@dataclass
class ObjectItemModel:
    path: str
    folder_name: str
    properties: dict | None
    status: bool  # True = Enabled, False = Disabled

    @property
    def actual_name(self) -> str:
        if self.properties and "actual_name" in self.properties:
            return self.properties["actual_name"]
        return self.folder_name.removeprefix(DISABLED_PREFIX)

    @property
    def display_name(self) -> str:
        if not self.status and self.actual_name:
            return self.actual_name
        return self.folder_name.removeprefix(DISABLED_PREFIX)

    @property
    def is_disabled_prefix_present(self) -> bool:
        return self.folder_name.lower().startswith(DISABLED_PREFIX.lower())

    @property
    def rarity(self) -> str:
        return (self.properties or {}).get("rarity", "").lower()

    @property
    def element(self) -> str:
        return (self.properties or {}).get("element", "").lower()

    @property
    def region(self) -> str:
        return (self.properties or {}).get("region", "").lower()

    @property
    def gender(self) -> str:
        return (self.properties or {}).get("gender", "").lower()

    @property
    def weapon(self) -> str:
        return (self.properties or {}).get("weapon", "").lower()

    @property
    def roles(self) -> list[str]:
        return (self.properties or {}).get("roles", [])

    @property
    def preset_name(self) -> Optional[str]:
        return (self.properties or {}).get("preset_name")
