from __future__ import annotations

import httpx

from ..settings import settings
from .rag import Source


def demo_answer(language: str, level: str, message: str, sources: list[Source]) -> dict:
    source_hint = f" Материал найден в «{sources[0].title}»." if sources else " Подходящий материал в базе не найден."
    if language == "English":
        explanation = "Цель: понять правило и сразу применить его в короткой английской фразе." + source_hint
        exercise = "Произнесите или напишите один собственный пример. Затем оцените уверенность от 1 до 5."
    else:
        explanation = "Цель: понять правило и сразу применить его в короткой испанской фразе." + source_hint
        exercise = "Произнесите или напишите один собственный пример. Затем оцените уверенность от 1 до 5."
    return {
        "mode": "demo",
        "answer": explanation,
        "exercise": exercise,
        "attempt_limit": 2,
        "sources": [{"title": s.title, "path": s.path} for s in sources],
        "note": "Добавьте OPENAI_API_KEY для генеративных ответов. Учебный сценарий и RAG уже работают.",
    }


async def answer(language: str, level: str, message: str, sources: list[Source], learner_notes: str = "") -> dict:
    if not settings.openai_api_key:
        return demo_answer(language, level, message, sources)
    context = "\n\n".join(f"SOURCE {s.path}\n{s.content[:3500]}" for s in sources)
    system = f"""Ты персональный AI-репетитор ДИС Lingua 360 для взрослого русскоязычного ученика.
Активный язык: {language}. Уровень: {level}. Цели: работа, путешествия и личное развитие.

ПРАВИЛА:
1. Никогда не смешивай English и Spanish в одном уроке. Русский используй только для краткого объяснения.
2. Следуй циклу: цель → объяснение → пример из RAG → практика → применение → рефлексия.
3. Приоритет источников: предоставленный контекст Obsidian, затем общеязыковое знание. Не выдумывай источник.
4. Если контекста недостаточно, прямо сообщи об этом и дай только безопасную базовую практику.
5. Коммуникативная пропорция: примерно 70% действия ученика и 30% объяснения.
6. Дай одну достижимую задачу, связанную с реальной ситуацией.
7. Исправляй не более двух самых важных ошибок за ответ.
8. После второй неудачной попытки измени способ объяснения и предложи вернуться к теме позже.
9. Учитывай уровень: не используй конструкции выше текущего уровня без пояснения.
10. Заверши вопросом для короткой рефлексии: что получилось и насколько уверенно от 1 до 5.

ФОРМАТ ОТВЕТА:
Цель: одна строка.
Объяснение: до 5 коротких предложений.
Пример: один пример на активном языке с переводом.
Практика: одно упражнение.
Самопроверка: чёткий критерий успеха.
Рефлексия: один вопрос.
"""
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Контекст Obsidian:\n{context}\n\nОшибки для персонализации:\n{learner_notes or 'Нет сохранённых ошибок'}\n\nЗапрос:\n{message}"},
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
