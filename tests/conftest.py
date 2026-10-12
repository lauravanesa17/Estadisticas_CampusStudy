import os

os.environ["SEED_ON_START"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, engine, get_db, SessionLocal
from app.main import app
from app.services import sincronizacion, tiempo

# Fecha fija para que las pruebas no dependan del día en que se corren.
AHORA_PRUEBAS = datetime(2026, 10, 12, 10, 0, tzinfo=tiempo.ZONA_COLOMBIA)


class Reloj:
    def __init__(self, momento: datetime) -> None:
        self.momento = momento

    def __call__(self) -> datetime:
        return self.momento


@pytest.fixture(autouse=True)
def reloj(monkeypatch):
    """Congela tiempo.ahora(). Para mover el reloj: reloj.momento = datetime(..., tzinfo=ZONA_COLOMBIA)."""
    fijo = Reloj(AHORA_PRUEBAS)
    monkeypatch.setattr(tiempo, "_reloj", fijo)
    return fijo


@pytest.fixture(autouse=True)
def sin_servicios_externos(monkeypatch):
    for nombre in ("usuarios_service_url", "materias_service_url", "tareas_service_url", "grupos_service_url", "servicio_token"):
        monkeypatch.setattr(settings, nombre, "")


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def servicios(monkeypatch):
    """Simula usuarios/tareas/materias/grupos con httpx.MockTransport.

    `servicios.rutas[(host, path)]` = cuerpo JSON, un código de estado (int) o una función(request).
    `servicios.caidos` = hosts que no responden (error de conexión).
    """

    class Simulados:
        def __init__(self) -> None:
            self.rutas: dict[tuple[str, str], object] = {}
            self.caidos: set[str] = set()
            self.peticiones: list[httpx.Request] = []

        def manejar(self, request: httpx.Request) -> httpx.Response:
            self.peticiones.append(request)
            if request.url.host in self.caidos:
                raise httpx.ConnectError("conexión rechazada", request=request)
            respuesta = self.rutas.get((request.url.host, request.url.path), 404)
            if callable(respuesta):
                respuesta = respuesta(request)
            if isinstance(respuesta, int):
                return httpx.Response(respuesta, json={"codigo": respuesta, "mensaje": "simulado"})
            return httpx.Response(200, json=respuesta)

    simulados = Simulados()
    monkeypatch.setattr(settings, "usuarios_service_url", "http://usuarios")
    monkeypatch.setattr(settings, "tareas_service_url", "http://tareas")
    monkeypatch.setattr(settings, "materias_service_url", "http://materias")
    monkeypatch.setattr(settings, "grupos_service_url", "http://grupos")
    monkeypatch.setattr(
        sincronizacion,
        "_crear_cliente",
        lambda: httpx.Client(transport=httpx.MockTransport(simulados.manejar)),
    )
    return simulados
