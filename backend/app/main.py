# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Імпортуємо наш новий роутер з папки api
from app.api.users import router as users_router 
from app.api.trips import router as trips_router
from app.api.bookings import router as bookings_router
from app.api.admin import router as admin_router

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Drogobych Express Taxi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключаємо роутер
app.include_router(users_router, prefix="/api")
app.include_router(trips_router, prefix="/api")
app.include_router(bookings_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_PANEL_DIR = os.path.join(BASE_DIR, "admin")
app.mount("/admin", StaticFiles(directory=ADMIN_PANEL_DIR, html=True), name="admin")


@app.get("/")
async def root():
    return {"message": "API is running"}