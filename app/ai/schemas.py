from pydantic import BaseModel

class AIDecision(BaseModel):
    engine: str
    direction: str
    confidence: float
    reason: str = ''
    weight: float = 1.0
