from dataclasses import dataclass
from app.core.constants import DISABLED_PREFIX


@dataclass
class FolderItemModel:
    path: str
    folder_name: str
    info: dict | None
    status: bool  # True = Enabled, False = Disabled

    @property
    def actual_name(self) -> str:
        if self.info and "actual_name" in self.info:
            return self.info["actual_name"]
        return self.folder_name.removeprefix(DISABLED_PREFIX)

    @property
    def display_name(self) -> str:
        if not self.status and self.actual_name:
            return self.actual_name
        return self.folder_name.removeprefix(DISABLED_PREFIX)

    @property
    def description(self) -> str:
        return self.info.get("description", "") if self.info else ""

    @property
    def is_safe(self) -> bool:
        return self.info.get("is_safe", False) if self.info else False
