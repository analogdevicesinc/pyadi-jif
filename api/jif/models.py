"""API data models for queries and returns."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

class ClockSearch(BaseModel):
    part: str
    vcxo: int
    output_clocks: List[int]
    custom_props: Optional[Dict]

class ClockUpdate(BaseModel):
    part: str
    config: Any