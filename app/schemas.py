from typing import Literal

from pydantic import BaseModel, Field


Language = Literal["English", "Spanish"]


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)


class SessionRequest(BaseModel):
    language: Language
    topic: str = Field(min_length=2, max_length=100)


class TutorRequest(BaseModel):
    language: Language
    level: str = Field(pattern=r"^(A0|A1|A2|B1|B2)$")
    message: str = Field(min_length=2, max_length=2000)


class ExerciseRequest(BaseModel):
    language: Language
    answer: str = Field(min_length=1, max_length=2000)
    attempt: int = Field(ge=1, le=2)


class VideoStatusRequest(BaseModel):
    status: Literal["candidate", "approved", "archived"]

