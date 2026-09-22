from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path

import httpx

from ..settings import settings


@dataclass(frozen=True)
class ReadingPassage:
    id: str
    day: int
    title: str
    text: str
    translation: str
    focus: tuple[str, ...]


PASSAGES = [
    ReadingPassage(
        "sprint-01", 1, "Знакомство",
        "I am Dmitry. My name is Dmitry. I am at home.",
        "Я Дмитрий. Меня зовут Дмитрий. Я дома.",
        ("I", "am", "my", "name", "home"),
    ),
    ReadingPassage(
        "sprint-02", 2, "Моя профессия",
        "I am a doctor. I help people. I read every day.",
        "Я врач. Я помогаю людям. Я читаю каждый день.",
        ("doctor", "help", "people", "read", "day"),
    ),
    ReadingPassage(
        "sprint-03", 3, "Работа и технологии",
        "I work with people and technology. I use a computer at work.",
        "Я работаю с людьми и технологиями. Я использую компьютер на работе.",
        ("work", "with", "people", "technology", "computer"),
    ),
    ReadingPassage(
        "sprint-04", 4, "Онлайн-встреча",
        "Today I have a short online meeting. I listen, ask questions, and take notes.",
        "Сегодня у меня короткая онлайн-встреча. Я слушаю, задаю вопросы и делаю заметки.",
        ("today", "short", "meeting", "listen", "questions"),
    ),
    ReadingPassage(
        "sprint-05", 5, "Рассказ о себе",
        "Hello. My name is Dmitry. I am a doctor and an AI specialist. I work with people and technology. I am learning English for work and travel.",
        "Здравствуйте. Меня зовут Дмитрий. Я врач и специалист по искусственному интеллекту. Я работаю с людьми и технологиями. Я учу английский для работы и путешествий.",
        ("hello", "doctor", "specialist", "technology", "English", "travel"),
    ),
]


def passage_by_id(passage_id: str) -> ReadingPassage | None:
    return next((item for item in PASSAGES if item.id == passage_id), None)


def public_passages() -> list[dict]:
    return [{**asdict(item), "focus": list(item.focus)} for item in PASSAGES]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def _edit_distance(expected: list[str], heard: list[str]) -> int:
    previous = list(range(len(heard) + 1))
    for row, expected_word in enumerate(expected, start=1):
        current = [row]
        for col, heard_word in enumerate(heard, start=1):
            current.append(min(
                current[-1] + 1,
                previous[col] + 1,
                previous[col - 1] + (expected_word != heard_word),
            ))
        previous = current
    return previous[-1]


def compare_reading(expected_text: str, transcript: str) -> dict:
    expected = _words(expected_text)
    heard = _words(transcript)
    distance = _edit_distance(expected, heard)
    accuracy = max(0, round(100 * (1 - distance / max(1, len(expected)))))
    issues: list[dict] = []

    matcher = SequenceMatcher(a=expected, b=heard, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            size = max(i2 - i1, j2 - j1)
            for offset in range(size):
                correct = expected[i1 + offset] if i1 + offset < i2 else ""
                actual = heard[j1 + offset] if j1 + offset < j2 else ""
                issues.append({"type": "replace", "expected": correct, "heard": actual})
        elif tag == "delete":
            issues.extend({"type": "missing", "expected": word, "heard": ""} for word in expected[i1:i2])
        elif tag == "insert":
            issues.extend({"type": "extra", "expected": "", "heard": word} for word in heard[j1:j2])

    focus_words = []
    for issue in issues:
        word = issue["expected"]
        if word and word not in focus_words:
            focus_words.append(word)

    if accuracy >= 90:
        summary = "Текст прочитан уверенно. Повторите ещё один раз без подсказки."
    elif accuracy >= 75:
        summary = "Основа получилась. Отработайте отмеченные слова и прочитайте текст повторно."
    else:
        summary = "Сначала прослушайте эталон по фразам, затем повторите каждую фразу отдельно."

    return {
        "accuracy": accuracy,
        "expected_words": len(expected),
        "heard_words": len(heard),
        "issues": issues[:8],
        "focus_words": focus_words[:4],
        "summary": summary,
        "disclaimer": "Проверка показывает, какие слова распознала модель. Она не является точной фонетической экспертизой отдельных звуков.",
    }


async def transcribe(content: bytes, filename: str, content_type: str, expected_text: str) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("Для проверки чтения нужен настроенный OPENAI_API_KEY")
    files = {"file": (filename, content, content_type)}
    data = {
        "model": settings.openai_transcription_model,
        "language": "en",
        "prompt": f"The learner is reading this exact American English text: {expected_text}",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            files=files,
            data=data,
        )
        response.raise_for_status()
    return response.json().get("text", "").strip()


async def reference_audio(passage: ReadingPassage, speed: str) -> bytes:
    if not settings.openai_api_key:
        raise RuntimeError("Для эталонного аудио нужен настроенный OPENAI_API_KEY")
    settings.reference_audio_path.mkdir(parents=True, exist_ok=True)
    cache_path = settings.reference_audio_path / f"{passage.id}_{speed}.mp3"
    if cache_path.exists():
        return cache_path.read_bytes()

    pace = "very slowly, with clear pauses between short phrases" if speed == "slow" else "clearly at a natural beginner-friendly pace"
    payload = {
        "model": settings.openai_tts_model,
        "voice": settings.openai_tts_voice,
        "input": passage.text,
        "instructions": f"Read in neutral American English, {pace}. Do not add any words.",
        "response_format": "mp3",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=payload,
        )
        response.raise_for_status()
    cache_path.write_bytes(response.content)
    return response.content
