from __future__ import annotations

from dataclasses import asdict, dataclass


SKILLS = ("speaking", "listening", "reading", "writing", "vocabulary", "pronunciation")

SKILL_LABELS = {
    "speaking": "Говорение",
    "listening": "Аудирование",
    "reading": "Чтение",
    "writing": "Письмо",
    "vocabulary": "Словарь",
    "pronunciation": "Произношение",
}

WEEK_PLAN = [
    {"day": "Понедельник", "language": "English", "focus": "Грамматика + практика", "minutes": 70},
    {"day": "Вторник", "language": "English", "focus": "Аудирование + говорение", "minutes": 70},
    {"day": "Среда", "language": "Spanish", "focus": "Грамматика + практика", "minutes": 45},
    {"day": "Четверг", "language": "Spanish", "focus": "Аудирование + говорение", "minutes": 45},
    {"day": "Пятница", "language": "English", "focus": "Чтение + письмо", "minutes": 70},
    {"day": "Суббота", "language": "Review", "focus": "Необязательное повторение без смешивания языков", "minutes": 0},
    {"day": "Воскресенье", "language": "Rest", "focus": "Отдых или видео без задания", "minutes": 0},
]

LESSON_STEPS = [
    "Цель урока",
    "Короткое объяснение",
    "Пример из Obsidian",
    "Аудирование или видео",
    "Голосовая практика",
    "Диалог с AI",
    "Письменное задание",
    "Разбор двух главных ошибок",
    "Рефлексия",
    "Интервальное повторение",
]


@dataclass(frozen=True)
class Lesson:
    id: str
    language: str
    level: str
    title: str
    objective: str
    topic: str
    phrase: str
    writing_task: str
    minutes: int = 20


LESSONS = [
    Lesson("en-a0-01", "English", "A0", "Первое знакомство", "Поздороваться и представиться", "greetings", "Hello, my name is Dmitry.", "Напишите два предложения о себе."),
    Lesson("en-a0-02", "English", "A0", "Звук TH", "Произнести /θ/ в трёх словах и фразе", "th-sound", "I think three times.", "Составьте предложение со словом think."),
    Lesson("en-a0-03", "English", "A0", "Работа и профессия", "Кратко рассказать о своей работе", "work-introduction", "I work with people and technology.", "Напишите три простых предложения о своей работе."),
    Lesson("en-a1-01", "English", "A1", "Поездка и аэропорт", "Задать три вопроса в аэропорту", "airport", "Where is the check-in desk?", "Напишите короткий диалог в аэропорту."),
    Lesson("es-a0-01", "Spanish", "A0", "Первое знакомство", "Поздороваться и представиться", "greetings", "Hola, me llamo Dmitry.", "Напишите два предложения о себе."),
    Lesson("es-a0-02", "Spanish", "A0", "Пять гласных", "Чётко произнести a, e, i, o, u", "vowels", "Una casa bonita.", "Напишите пять слов — по одному на каждую гласную."),
    Lesson("es-a0-03", "Spanish", "A0", "Работа и профессия", "Назвать профессию и место работы", "work-introduction", "Trabajo con personas y tecnología.", "Напишите три простых предложения о своей работе."),
    Lesson("es-a1-01", "Spanish", "A1", "Путешествие", "Спросить дорогу и понять простой ответ", "travel", "¿Dónde está la estación?", "Напишите короткий диалог на улице."),
]


def lessons_for(language: str) -> list[dict]:
    return [asdict(item) for item in LESSONS if item.language == language]


def next_lesson(language: str, completed_ids: set[str]) -> dict:
    route = [item for item in LESSONS if item.language == language]
    lesson = next((item for item in route if item.id not in completed_ids), route[-1])
    result = asdict(lesson)
    result["steps"] = LESSON_STEPS
    return result
