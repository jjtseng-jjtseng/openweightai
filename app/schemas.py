from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Profile(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, examples=["Maya"])
    age: int | None = Field(default=None, ge=0, le=130, examples=[34])
    likes: list[str] = Field(default_factory=list, examples=[["coffee", "gardening"]])
    income: str | None = Field(default=None, examples=["$72,000 per year"])
    state: str | None = Field(default=None, examples=["California"])
    extra: dict[str, Any] = Field(default_factory=dict)


class QuestionRequest(BaseModel):
    profile: Profile
    question: str = Field(..., min_length=1, examples=["What is your salary?"])
    max_tokens: int = Field(default=160, ge=16, le=512)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    include_raw: bool = False


class AnswerResponse(BaseModel):
    answer: str
    source: Literal["profile", "attention_check", "general_knowledge", "unknown", "model_raw"]
    confidence: float = Field(ge=0.0, le=1.0)
    used_profile_fields: list[str] = Field(default_factory=list)
    model: str
    latency_ms: int
    raw_text: str | None = None
    usage: dict[str, Any] | None = None


class WarmupResponse(BaseModel):
    ok: bool
    model: str
    latency_ms: int

