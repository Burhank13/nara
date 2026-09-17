from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.auth import router as auth_router
from app.routes.invites import router as invites_router
from app.routes.locations import router as locations_router
from app.routes.shifts import router as shifts_router
from app.routes.team import router as team_router

app = FastAPI(title="Nara Shift Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(invites_router)
app.include_router(team_router)
app.include_router(locations_router)
app.include_router(shifts_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
