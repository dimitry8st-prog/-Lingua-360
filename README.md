# ДИС Lingua 360

Персональный AI-репетитор английского и испанского языков с отдельными учебными маршрутами, RAG по Obsidian, фонетическими материалами YouTube и записью голоса.

![Статус](https://img.shields.io/badge/MVP-working-f38b2a) ![Python](https://img.shields.io/badge/FastAPI-0.141-114c86) ![Docker](https://img.shields.io/badge/Docker-ready-0b2d52)

## Что уже работает

- закрытый персональный кабинет;
- английский 70% и испанский 30%;
- отдельный контекст для каждого языка;
- AI-репетитор через OpenAI API и безопасный демо-режим без ключа;
- RAG-поиск по Markdown-заметкам Obsidian;
- источники в ответах репетитора;
- одобренные ссылки на YouTube для фонетики;
- запись и сохранение голоса в браузере;
- журнал прогресса и ограничение до двух попыток;
- Telegram-заглушка;
- Docker и healthcheck.

## Быстрый локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

Откройте `http://127.0.0.1:8000`.

Демо-вход:

- email: `demo@lingua.local`
- пароль: `demo123`

Перед публикацией на VPS обязательно замените `OWNER_PASSWORD` и `APP_SECRET_KEY`.

Тесты:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Запуск в Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Проверка: `http://SERVER_IP:8000/health`.

## OpenAI и YouTube

Добавьте ключи в `.env`:

```env
OPENAI_API_KEY=...
YOUTUBE_API_KEY=...
```

Без `OPENAI_API_KEY` проект работает в демонстрационном режиме и показывает заранее заданный учебный ответ с найденными RAG-источниками. Без YouTube API сайт открывает безопасный поисковый запрос; автоматическое добавление видео намеренно не выполняется без ручного одобрения.

## Структура

```text
app/              FastAPI, авторизация, RAG, AI и API
static/           адаптивный интерфейс сайта
obsidian-vault/   учебная база English и Spanish
data/             SQLite и голосовые записи
tests/            smoke- и validation-тесты
Dockerfile        контейнер приложения
docker-compose.yml
```

## Ограничения MVP

- один владелец; модель данных готова к расширению;
- автоматическая оценка произношения пока не включена;
- SQLite используется в локальном MVP, на этапе масштабирования предусмотрен PostgreSQL;
- текущий RAG — прозрачный локальный поиск по Obsidian; векторный Qdrant подключается после накопления базы;
- Telegram отключён переменной `TELEGRAM_ENABLED=false`.

Автор: **Степанов Д.А.**
