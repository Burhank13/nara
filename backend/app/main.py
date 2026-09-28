from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import middleware, observability
from app.config import settings
from app.database import get_db
from app.errors import api_error
from app.routes.auth import router as auth_router
from app.routes.availability import router as availability_router
from app.routes.business import router as business_router
from app.routes.invites import router as invites_router
from app.routes.locations import router as locations_router
from app.routes.overview import router as overview_router
from app.routes.payroll import router as payroll_router
from app.routes.shifts import router as shifts_router
from app.routes.team import router as team_router
from app.routes.timesheets import router as timesheets_router

API_PREFIX = "/api"

observability.init()

app = FastAPI(title="Nara Shift Tracker")

middleware.install(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Everything the API answers lives under /api, so no endpoint can ever shadow a page of the
# single-page app: /overview, /team and /timesheets are both, and the SPA needs the deep links.
for router in (
    auth_router,
    invites_router,
    team_router,
    locations_router,
    shifts_router,
    availability_router,
    overview_router,
    timesheets_router,
    business_router,
    payroll_router,
):
    app.include_router(router, prefix=API_PREFIX)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness: is the process answering at all. Kept free of dependencies on purpose."""
    return {"status": "ok"}


@app.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness: only report healthy once the database is actually reachable."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise api_error(503, "database_unavailable", "The database is not reachable.") from exc
    return {"status": "ready"}


def _serve_built_frontend(directory: Path) -> None:
    """One origin in production, which is what lets the refresh cookie stay SameSite=lax."""
    app.mount("/assets", StaticFiles(directory=directory / "assets"), name="assets")
    index = directory / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        candidate = (directory / path).resolve()
        # Only ever serve files from inside the build directory, whatever the URL asks for.
        if path and candidate.is_file() and candidate.is_relative_to(directory.resolve()):
            return FileResponse(candidate)
        return FileResponse(index)


_static_dir = Path(settings.static_dir)
if (_static_dir / "index.html").is_file():
    _serve_built_frontend(_static_dir)
