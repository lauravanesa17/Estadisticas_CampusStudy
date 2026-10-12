from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import estadisticas, eventos, salud
from app.seed import seed_si_vacio

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.seed_on_start:
        db = SessionLocal()
        try:
            seed_si_vacio(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="CampusStudy — Estadísticas",
    description=(
        "Microservicio de estadísticas de CampusStudy. "
        "Consulta a usuarios, materias, tareas y grupos, mantiene una caché local "
        "y expone reportes agregados según el contrato /api/v1 del Frontend."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

origenes = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if origenes == ["*"] else origenes,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validacion_invalida(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"codigo": 400, "mensaje": "Solicitud incorrecta (parámetro inválido)."},
    )


# Se registra sobre la clase de Starlette para cubrir también los 404/405 de rutas
# inexistentes, que no pasan por el HTTPException de FastAPI.
@app.exception_handler(StarletteHTTPException)
async def error_http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"codigo": exc.status_code, "mensaje": str(exc.detail)},
    )


app.include_router(salud.router)
app.include_router(eventos.router)
app.include_router(estadisticas.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")
