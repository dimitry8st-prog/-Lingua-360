from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import connection, init_db, utcnow, verify_password
from .schemas import (
    ExerciseRequest,
    LessonCompleteRequest,
    LoginRequest,
    ReflectionRequest,
    SessionRequest,
    TutorRequest,
    VideoStatusRequest,
)
from .services.curriculum import LESSONS, SKILL_LABELS, WEEK_PLAN, lessons_for, next_lesson
from .services.rag import load_sources, search
from .services.tutor import answer
from .settings import BASE_DIR, settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("lingua360")
STATIC = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("Lingua 360 started; telegram_enabled=%s", settings.telegram_enabled)
    yield


app = FastAPI(title="ДИС Lingua 360", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Требуется авторизация")
    token = authorization.removeprefix("Bearer ").strip()
    with connection() as db:
        row = db.execute(
            "SELECT users.id,users.email,users.role FROM tokens JOIN users ON users.id=tokens.user_id WHERE token=?",
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Сессия недействительна")
    return dict(row)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "rag_documents": len(load_sources()), "telegram": "enabled" if settings.telegram_enabled else "disabled"}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    with connection() as db:
        row = db.execute("SELECT * FROM users WHERE email=?", (payload.email.lower(),)).fetchone()
        if not row or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(401, "Неверный email или пароль")
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO tokens(token,user_id,created_at) VALUES(?,?,?)", (token, row["id"], utcnow()))
    return {"token": token, "user": {"name": "Дмитрий", "email": row["email"], "role": row["role"]}}


@app.get("/api/dashboard")
def dashboard(user=Depends(current_user)):
    with connection() as db:
        progress = [dict(r) for r in db.execute("SELECT language,level,lessons,minutes,xp FROM progress WHERE user_id=?", (user["id"],))]
        errors = db.execute("SELECT COUNT(*) count FROM errors WHERE user_id=?", (user["id"],)).fetchone()["count"]
        voices = db.execute("SELECT COUNT(*) count FROM voice_records WHERE user_id=?", (user["id"],)).fetchone()["count"]
        completed = {r["lesson_id"] for r in db.execute("SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user["id"],))}
        skill_rows = [dict(r) for r in db.execute(
            "SELECT language,skill,score,samples FROM skill_progress WHERE user_id=? ORDER BY language,skill", (user["id"],)
        )]
    return {"user": user, "progress": progress, "errors": errors, "voices": voices,
            "plan": {language: next_lesson(language, completed) for language in ("English", "Spanish")},
            "skills": [{**row, "label": SKILL_LABELS[row["skill"]]} for row in skill_rows],
            "week": WEEK_PLAN}


@app.get("/api/learning/plan")
def learning_plan(user=Depends(current_user)):
    with connection() as db:
        completed = {r["lesson_id"] for r in db.execute("SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user["id"],))}
    return {
        "allocation": {"English": 70, "Spanish": 30},
        "week": WEEK_PLAN,
        "routes": {
            language: [{**item, "completed": item["id"] in completed} for item in lessons_for(language)]
            for language in ("English", "Spanish")
        },
    }


@app.get("/api/learning/today")
def today_lesson(language: str, user=Depends(current_user)):
    if language not in ("English", "Spanish"):
        raise HTTPException(422, "Неизвестный язык")
    with connection() as db:
        completed = {r["lesson_id"] for r in db.execute("SELECT lesson_id FROM lesson_completions WHERE user_id=?", (user["id"],))}
    return next_lesson(language, completed)


@app.post("/api/learning/complete")
def complete_lesson(payload: LessonCompleteRequest, user=Depends(current_user)):
    lesson = next((item for item in LESSONS if item.id == payload.lesson_id), None)
    if not lesson or lesson.language != payload.language:
        raise HTTPException(422, "Урок не соответствует выбранному языку")
    now = utcnow()
    with connection() as db:
        existing = db.execute(
            "SELECT 1 FROM lesson_completions WHERE user_id=? AND lesson_id=?", (user["id"], payload.lesson_id)
        ).fetchone()
        if existing:
            return {"completed": True, "already_completed": True, "lesson_id": payload.lesson_id}
        db.execute(
            "INSERT INTO lesson_completions(user_id,lesson_id,language,minutes,created_at) VALUES(?,?,?,?,?)",
            (user["id"], payload.lesson_id, payload.language, payload.minutes, now),
        )
        for skill in set(payload.practiced_skills):
            db.execute(
                "UPDATE skill_progress SET score=MIN(100,score+8),samples=samples+1,updated_at=? "
                "WHERE user_id=? AND language=? AND skill=?",
                (now, user["id"], payload.language, skill),
            )
        db.execute(
            "UPDATE progress SET lessons=lessons+1,minutes=minutes+?,xp=xp+20 WHERE user_id=? AND language=?",
            (payload.minutes, user["id"], payload.language),
        )
        a0_ids = {item.id for item in LESSONS if item.language == payload.language and item.level == "A0"}
        completed_a0 = {r["lesson_id"] for r in db.execute(
            "SELECT lesson_id FROM lesson_completions WHERE user_id=? AND language=?", (user["id"], payload.language)
        )}
        if a0_ids.issubset(completed_a0):
            db.execute("UPDATE progress SET level='A1' WHERE user_id=? AND language=?", (user["id"], payload.language))
    return {"completed": True, "already_completed": False, "lesson_id": payload.lesson_id, "xp_added": 20}


@app.post("/api/reflections")
def save_reflection(payload: ReflectionRequest, user=Depends(current_user)):
    with connection() as db:
        cur = db.execute(
            "INSERT INTO reflections(user_id,language,lesson_id,confidence,learned,difficult,created_at) VALUES(?,?,?,?,?,?,?)",
            (user["id"], payload.language, payload.lesson_id, payload.confidence, payload.learned, payload.difficult, utcnow()),
        )
    return {"saved": True, "id": cur.lastrowid}


@app.get("/api/reviews")
def review_queue(language: str | None = None, user=Depends(current_user)):
    params: list[object] = [user["id"]]
    where = "user_id=?"
    if language:
        if language not in ("English", "Spanish"):
            raise HTTPException(422, "Неизвестный язык")
        where += " AND language=?"
        params.append(language)
    with connection() as db:
        rows = [dict(r) for r in db.execute(
            f"SELECT id,language,category,example,count,next_review_at,created_at FROM errors WHERE {where} ORDER BY COALESCE(next_review_at,created_at)",
            params,
        )]
    now = utcnow()
    return [{**row, "due": not row["next_review_at"] or row["next_review_at"] <= now} for row in rows]


@app.post("/api/sessions")
def create_session(payload: SessionRequest, user=Depends(current_user)):
    with connection() as db:
        cur = db.execute("INSERT INTO sessions(user_id,language,topic,created_at) VALUES(?,?,?,?)",
                         (user["id"], payload.language, payload.topic, utcnow()))
    return {"id": cur.lastrowid, "language": payload.language, "topic": payload.topic}


@app.post("/api/tutor/respond")
async def tutor(payload: TutorRequest, user=Depends(current_user)):
    sources = search(payload.message, payload.language, payload.level)
    with connection() as db:
        mistakes = [r["example"] for r in db.execute(
            "SELECT example FROM errors WHERE user_id=? AND language=? ORDER BY id DESC LIMIT 3",
            (user["id"], payload.language),
        )]
    result = await answer(payload.language, payload.level, payload.message, sources, "; ".join(mistakes))
    logger.info("tutor user=%s language=%s mode=%s sources=%s", user["id"], payload.language, result["mode"], len(sources))
    return result


@app.post("/api/exercises/submit")
def submit_exercise(payload: ExerciseRequest, user=Depends(current_user)):
    if payload.attempt >= 2:
        feedback = "Попытка сохранена. Возвращаемся к ошибке позже, без зацикливания."
        review_at = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        with connection() as db:
            db.execute("INSERT INTO errors(user_id,language,category,example,next_review_at,created_at) VALUES(?,?,?,?,?,?)",
                       (user["id"], payload.language, "practice", payload.answer[:200], review_at, utcnow()))
    else:
        feedback = "Хорошая первая попытка. Исправьте одну деталь и повторите ещё раз."
    with connection() as db:
        db.execute("UPDATE progress SET lessons=lessons+1,xp=xp+10,minutes=minutes+5 WHERE user_id=? AND language=?",
                   (user["id"], payload.language))
    return {"feedback": feedback, "next_action": "finish" if payload.attempt >= 2 else "retry", "attempt": payload.attempt,
            "review_in_days": 2 if payload.attempt >= 2 else None}


@app.get("/api/videos")
def videos(language: str | None = None, user=Depends(current_user)):
    with connection() as db:
        if language:
            rows = db.execute("SELECT * FROM videos WHERE status='approved' AND language=?", (language,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM videos WHERE status='approved'").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/admin/youtube/search")
def youtube_search(language: str, topic: str, user=Depends(current_user)):
    accent = "American" if language == "English" else "Latin American"
    query = f"{accent} {language} {topic} pronunciation articulation beginner".replace(" ", "+")
    return {"mode": "search-link", "candidates": [{"title": f"Поиск: {topic}", "url": f"https://www.youtube.com/results?search_query={query}", "status": "candidate"}],
            "note": "Для автоматического каталога добавьте YOUTUBE_API_KEY; ручное одобрение остаётся обязательным."}


@app.patch("/api/admin/videos/{video_id}")
def update_video(video_id: int, payload: VideoStatusRequest, user=Depends(current_user)):
    with connection() as db:
        result = db.execute("UPDATE videos SET status=? WHERE id=?", (payload.status, video_id))
    if not result.rowcount:
        raise HTTPException(404, "Видео не найдено")
    return {"id": video_id, "status": payload.status}


@app.post("/api/admin/rag/reindex")
def reindex(user=Depends(current_user)):
    docs = load_sources()
    return {"status": "indexed", "documents": len(docs), "mode": "local-markdown"}


@app.post("/api/voice")
async def upload_voice(language: str, audio: UploadFile = File(...), user=Depends(current_user)):
    if language not in ("English", "Spanish"):
        raise HTTPException(422, "Неизвестный язык")
    content = await audio.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Файл больше 10 МБ")
    suffix = Path(audio.filename or "recording.webm").suffix or ".webm"
    filename = f"{user['id']}_{secrets.token_hex(8)}{suffix}"
    (settings.voice_path / filename).write_bytes(content)
    with connection() as db:
        cur = db.execute("INSERT INTO voice_records(user_id,language,filename,content_type,created_at) VALUES(?,?,?,?,?)",
                         (user["id"], language, filename, audio.content_type, utcnow()))
    return {"id": cur.lastrowid, "filename": filename, "size": len(content)}


@app.get("/api/voice")
def list_voice(user=Depends(current_user)):
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT id,language,filename,created_at FROM voice_records WHERE user_id=? ORDER BY id DESC", (user["id"],))]


@app.get("/api/voice/{voice_id}/file")
def voice_file(voice_id: int, user=Depends(current_user)):
    with connection() as db:
        row = db.execute("SELECT filename,content_type FROM voice_records WHERE id=? AND user_id=?", (voice_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(404, "Запись не найдена")
    return FileResponse(settings.voice_path / row["filename"], media_type=row["content_type"] or "audio/webm")


@app.delete("/api/voice/{voice_id}")
def delete_voice(voice_id: int, user=Depends(current_user)):
    with connection() as db:
        row = db.execute("SELECT filename FROM voice_records WHERE id=? AND user_id=?", (voice_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(404, "Запись не найдена")
        db.execute("DELETE FROM voice_records WHERE id=?", (voice_id,))
    path = settings.voice_path / row["filename"]
    if path.exists():
        path.unlink()
    return {"deleted": True}


@app.get("/api/integrations")
def integrations(user=Depends(current_user)):
    return {
        "openai": "configured" if settings.openai_api_key else "demo",
        "youtube": "configured" if settings.youtube_api_key else "search-link",
        "obsidian": "connected",
        "telegram": "enabled" if settings.telegram_enabled else "disabled",
    }
