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


class LessonCompleteRequest(BaseModel):
    lesson_id: str = Field(pattern=r"^(en|es)-(a0|a1|a2|b1|b2)-\d{2}$")
    language: Language
    minutes: int = Field(ge=5, le=180)
    practiced_skills: list[Literal["speaking", "listening", "reading", "writing", "vocabulary", "pronunciation"]]


class ReflectionRequest(BaseModel):
    language: Language
    lesson_id: str = Field(min_length=5, max_length=30)
    confidence: int = Field(ge=1, le=5)
    learned: str = Field(min_length=2, max_length=500)
    difficult: str = Field(default="", max_length=500)
