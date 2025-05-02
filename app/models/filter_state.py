from dataclasses import dataclass, field
from typing import Literal, Set, Dict
import hashlib
import json


@dataclass
class FilterState:
    text: str = ""
    status: Literal["All", "Enabled", "Disabled"] = "All"
    metadata: Dict[str, Set[str]] = field(default_factory=dict)

    def is_same_as(self, other: "FilterState") -> bool:
        return (
            self.text == other.text
            and self.status == other.status
            and self.metadata == other.metadata
        )

    def hash(self) -> str:
        """Return a hash of the filter state for caching."""
        data = {
            "text": self.text.strip().lower(),
            "status": self.status,
            "metadata": {k: sorted(list(v)) for k, v in sorted(self.metadata.items())},
        }
        encoded = json.dumps(data, sort_keys=True)
        return hashlib.md5(encoded.encode("utf-8")).hexdigest()
