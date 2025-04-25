from dataclasses import dataclass
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
