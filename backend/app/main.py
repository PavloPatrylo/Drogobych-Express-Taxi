# app/main.py

from fastapi import FastAPI, APIRouter
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Імпортуємо роутери
from app.api.auth import router as public_auth_router
from app.api.users import router as users_router 
from app.api.trips import router as trips_router
from app.api.bookings import router as bookings_router
from app.api.admin import audit, auth, broadcast, crm, finance, schedule, vehicles

from app.api.ws import router as ws_router

from app.core.config import settings

app = FastAPI(title="Drogobych Express Taxi API")

admin_router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_custom_headers(request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Підключаємо роутери
app.include_router(ws_router)
app.include_router(public_auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(trips_router, prefix="/api")
app.include_router(bookings_router, prefix="/api")

admin_router.include_router(auth.router, prefix="/api/admin")
admin_router.include_router(vehicles.router, prefix="/api/admin")
admin_router.include_router(schedule.router, prefix="/api/admin")
admin_router.include_router(crm.router, prefix="/api/admin")
admin_router.include_router(finance.router, prefix="/api/admin")
admin_router.include_router(broadcast.router, prefix="/api/admin")
admin_router.include_router(audit.router, prefix="/api/admin")

app.include_router(admin_router)

import asyncio
from app.services.reminders import start_reminder_scheduler
from bot.main_bot import dp, bot

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_reminder_scheduler())
    asyncio.create_task(dp.start_polling(bot, handle_signals=False))

from fastapi import FastAPI, APIRouter, Response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/health")
@app.get("/api/health")
async def healthcheck():
    return {"status": "ok", "service": "drogobych-express-taxi-backend"}

# Клієнтський Mini App (Пасажир / Водій)
@app.get("/")
@app.get("/miniapp")
@app.get("/miniapp/")
async def serve_index():
    """
    Головна сторінка клієнтського Mini App.
    """
    return FileResponse("index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/miniapp/app.js")
@app.get("/app.js")
async def serve_app_js():
    """
    JS скрипт для клієнтського Mini App.
    """
    return FileResponse("app.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
