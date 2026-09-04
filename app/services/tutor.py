from __future__ import annotations

import httpx

from ..settings import settings
from .rag import Source


def demo_answer(language: str, level: str, message: str, sources: list[Source]) -> dict:
    if language == "English":
        explanation = "Начнём с короткой практики. В американском английском звук TH произносится с кончиком языка между зубами и мягким выдохом."
        exercise = "Повторите медленно: think — three — thank. Затем скажите: I think three times."
    else:
        explanation = "Начнём с короткой практики. В латиноамериканском испанском пять гласных звучат стабильно: a, e, i, o, u."
        exercise = "Повторите: casa — mesa — vino — poco — luna. Затем скажите: Una casa bonita."
    return {
        "mode": "demo",
        "answer": explanation,
        "exercise": exercise,
        "attempt_limit": 2,
        "sources": [{"title": s.title, "path": s.path} for s in sources],
        "note": "Добавьте OPENAI_API_KEY для генеративных ответов. Учебный сценарий и RAG уже работают.",
    }


async def answer(language: str, level: str, message: str, sources: list[Source]) -> dict:
    if not settings.openai_api_key:
        return demo_answer(language, level, message, sources)
    context = "\n\n".join(f"SOURCE {s.path}\n{s.content[:3500]}" for s in sources)
    system = (
        "Ты персональный языковой репетитор ДИС Lingua 360. "
        f"Активный язык: {language}; уровень: {level}. Не смешивай языки. "
        "Опирайся на контекст. Если материала недостаточно, скажи об этом. "
        "Дай короткое объяснение, одно упражнение и не более двух замечаний."
    )
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Контекст:\n{context}\n\nЗапрос:\n{message}"},
        ],
        "temperature": 0.4,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"}, json=payload,
            )
            response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return {"mode": "openai", "answer": text, "exercise": "Ответьте на задание репетитора.", "attempt_limit": 2,
                "sources": [{"title": s.title, "path": s.path} for s in sources]}
    except Exception:
        result = demo_answer(language, level, message, sources)
        result["note"] = "OpenAI временно недоступен; включён безопасный демо-ответ."
        return result

