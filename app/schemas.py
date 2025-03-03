from pydantic import BaseModel
from typing import List, Optional


class IOC(BaseModel):
    type: str
    value: str
    context: Optional[str] = None
    confidence: int = 100


class SecurityAnalysis(BaseModel):
    iocs: List[IOC]
    sigma_rule: Optional[str] = None
