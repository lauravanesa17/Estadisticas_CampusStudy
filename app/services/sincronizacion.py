from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.services.eventos import aplicar_proyeccion


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and "datos" in payload:
        return payload["datos"]
    return payload


def _get(url: str) -> Any | None:
    try:
        with httpx.Client(timeout=settings.http_timeout_seconds) as cliente:
            respuesta = cliente.get(url)
            if respuesta.status_code == 404:
                return None
            if respuesta.status_code >= 400:
                raise ConnectionError(url)
            return _unwrap(respuesta.json())
    except httpx.HTTPError as exc:
        raise ConnectionError(str(exc)) from exc


def refrescar_usuario(db: Session, usuario_id: int) -> None:
    """Consulta a los demás servicios y actualiza la caché. Si no hay URLs, no hace nada."""
    if settings.usuarios_service_url:
        datos = _get(f"{settings.usuarios_service_url.rstrip('/')}/api/v1/usuarios/{usuario_id}")
        if datos:
            aplicar_proyeccion(db, "usuario.actualizado", datos)

    if settings.tareas_service_url:
        datos = _get(f"{settings.tareas_service_url.rstrip('/')}/api/v1/tareas?usuario_id={usuario_id}&tamano=100")
        if isinstance(datos, dict):
            for tarea in datos.get("tareas") or []:
                aplicar_proyeccion(db, "tarea.actualizada", tarea)

    if settings.materias_service_url:
        try:
            datos = _get(f"{settings.materias_service_url.rstrip('/')}/api/v1/materias?usuario_id={usuario_id}")
        except ConnectionError:
            datos = None
        if isinstance(datos, list):
            for materia in datos:
                aplicar_proyeccion(db, "materia.actualizada", materia)

    if settings.grupos_service_url:
        datos = _get(f"{settings.grupos_service_url.rstrip('/')}/api/v1/grupos")
        if isinstance(datos, list):
            for grupo in datos:
                integrantes = grupo.get("integrantes") or []
                pertenece = any(
                    (item.get("usuario_id") if isinstance(item, dict) else item) == usuario_id
                    for item in integrantes
                )
                if not pertenece:
                    continue
                aplicar_proyeccion(db, "grupo.actualizado", grupo)
