# app/main.py

from fastapi import FastAPI, APIRouter
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Імпортуємо роутери
from app.api.users import router as users_router 
from app.api.trips import router as trips_router
from app.api.bookings import router as bookings_router
from app.api.admin import audit, auth, broadcast, crm, finance, schedule, vehicles

app = FastAPI(title="Drogobych Express Taxi API")

admin_router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключаємо роутери
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

# Клієнтський Mini App (Пасажир / Водій)
@app.get("/")
async def serve_index():
    """
    Головна сторінка клієнтського Mini App.
    """
    return FileResponse("index.html")

@app.get("/app.js")
async def serve_app_js():
    """
    JS скрипт для клієнтського Mini App.
    """
    return FileResponse("app.js")
