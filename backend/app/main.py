# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Імпортуємо наш новий роутер з папки api
from app.api.users import router as users_router 
from app.api.trips import router as trips_router
from app.api.bookings import router as bookings_router

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

@app.get("/")
async def root():
    return {"message": "API is running"}