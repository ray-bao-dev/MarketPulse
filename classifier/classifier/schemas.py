from pydantic import BaseModel, Field, field_validator


class BarIn(BaseModel):
    t: str
    o: float
    h: float
    l: float
    c: float
    v: int
    vw: float | None = None
    n: int | None = None


class DetectRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    bars: list[BarIn] = Field(..., min_length=1)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        return value.upper()


class PatternOut(BaseModel):
    t: str
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    direction: str


class DetectResponse(BaseModel):
    model_version: str
    inference_mode: str
    patterns: list[PatternOut]
