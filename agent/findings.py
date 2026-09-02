from dataclasses import dataclass, asdict
from typing import Literal

Severity = Literal["low", "medium", "high", "critical"]


@dataclass
class Finding:
    tier: int
    category: str
    severity: Severity
    page_url: str
    title: str
    description: str = ""
    repro_steps: str = ""
    screenshot_url: str | None = None

    def to_row(self, job_id: str) -> dict:
        row = asdict(self)
        row["job_id"] = job_id
        return row
