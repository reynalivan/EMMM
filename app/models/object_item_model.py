# app/models/object_item_model.py

from dataclasses import dataclass
from typing import Optional
from app.core.constants import DISABLED_PREFIX


@dataclass
class ObjectItemModel:
    path: str
    folder_name: str
    properties: dict | None
    status: bool

    def __post_init__(self):
        self._init_metadata_index()

    def _init_metadata_index(self):
        props = self.properties or {}
        self._metadata_index: dict[str, set[str]] = {
            "rarity": {str(props.get("rarity", "")).lower()},
            "element": {str(props.get("element", "")).lower()},
            "region": {str(props.get("region", "")).lower()},
            "gender": {str(props.get("gender", "")).lower()},
            "weapon": {str(props.get("weapon", "")).lower()},
            "roles": (
                set(map(str.lower, props.get("roles", [])))
                if props.get("roles")
                else set()
            ),
        }

    @property
    def metadata_index(self) -> dict[str, set[str]]:
        return self._metadata_index

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
