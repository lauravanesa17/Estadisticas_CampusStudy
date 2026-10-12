"""Consulta a los demás microservicios y actualiza la caché local de estadísticas.

Principio del contrato (I.7 / H.7): "no hubo respuesta" no significa "no existe".
Cada servicio se consulta por separado; si uno falla, sus cambios se descartan,
se registra el error y el resto sigue. El router decide si sirve la caché o responde 503.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import MateriaProyeccion, MiembroGrupo, SincronizacionUsuario, TareaProyeccion, UsuarioProyeccion
from app.services.eventos import aplicar_proyeccion
from app.services.ids import entero_id, primer_id
from app.services.tiempo import ahora

log = logging.getLogger("estadisticas.sincronizacion")

TAMANO_PAGINA = 100
MAX_PAGINAS = 50


class DependenciaNoDisponible(Exception):
    def __init__(self, servicio: str, detalle: str = "") -> None:
        super().__init__(f"{servicio}: {detalle}")
        self.servicio = servicio
        self.detalle = detalle


@dataclass
class ResultadoSincronizacion:
    fallidos: list[str] = field(default_factory=list)
    registro: SincronizacionUsuario | None = None

    def ultima_actualizacion_de_fallidos(self) -> datetime | None:
        """Momento del dato más viejo entre los servicios que no respondieron."""
        if not self.registro:
            return None
        marcas = [getattr(self.registro, _CAMPO_POR_SERVICIO[s]) for s in self.fallidos]
        marcas = [m for m in marcas if m]
        return min(marcas) if marcas else None


_CAMPO_POR_SERVICIO = {
    "usuarios-service": "usuario_en",
    "tareas-service": "tareas_en",
    "materias-service": "materias_en",
    "grupos-service": "grupos_en",
}


def hay_servicios_configurados() -> bool:
    return any(
        (
            settings.usuarios_service_url,
            settings.tareas_service_url,
            settings.materias_service_url,
            settings.grupos_service_url,
        )
    )


def _crear_cliente() -> httpx.Client:
    # retries: reintenta solo fallos de conexión (servicio caído / puerto cerrado).
    return httpx.Client(
        timeout=settings.http_timeout_seconds,
        transport=httpx.HTTPTransport(retries=settings.http_reintentos),
    )


def _autorizacion(entrante: str | None) -> str | None:
    """Reenvía el token del Frontend; si no hay, usa el token de servicio configurado."""
    if entrante:
        return entrante
    if settings.servicio_token:
        return f"Bearer {settings.servicio_token}"
    return None


def _unwrap(payload: Any) -> Any:
    # tareas-service envuelve en {exito, datos, mensaje}; materias y grupos responden plano.
    if isinstance(payload, dict) and "datos" in payload:
        return payload["datos"]
    return payload


def _get(cliente: httpx.Client, servicio: str, url: str, token: str | None) -> Any | None:
    """Devuelve el cuerpo (sin envoltorio), None si el recurso no existe (404),
    o lanza DependenciaNoDisponible ante cualquier otra falla."""
    headers = {"Authorization": token} if token else {}
    try:
        respuesta = cliente.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise DependenciaNoDisponible(servicio, f"{type(exc).__name__}: {exc}") from exc
    if respuesta.status_code == 404:
        return None
    if respuesta.status_code >= 400:
        raise DependenciaNoDisponible(servicio, f"HTTP {respuesta.status_code} en {url}")
    try:
        cuerpo = respuesta.json()
    except ValueError as exc:
        raise DependenciaNoDisponible(servicio, f"respuesta no JSON en {url}") from exc
    if isinstance(cuerpo, dict) and cuerpo.get("exito") is False:
        raise DependenciaNoDisponible(servicio, f"exito=false en {url}")
    return _unwrap(cuerpo)


def _sincronizar_usuario(db: Session, cliente: httpx.Client, base: str, usuario_id: int, token: str | None) -> None:
    datos = _get(cliente, "usuarios-service", f"{base}/api/v1/usuarios/{usuario_id}", token)
    if datos is None:
        # El dueño del dato confirma que no existe: se quita de la caché para responder 404.
        usuario = db.get(UsuarioProyeccion, usuario_id)
        if usuario:
            db.delete(usuario)
        return
    if not isinstance(datos, dict):
        raise DependenciaNoDisponible("usuarios-service", "respuesta con forma inesperada")
    aplicar_proyeccion(db, "usuario.actualizado", {**datos, "usuario_id": usuario_id}, commit=False)


def _sincronizar_tareas(db: Session, cliente: httpx.Client, base: str, usuario_id: int, token: str | None) -> None:
    vistas: set[int] = set()
    completo = False
    for pagina in range(1, MAX_PAGINAS + 1):
        url = f"{base}/api/v1/tareas?usuario_id={usuario_id}&pagina={pagina}&tamano={TAMANO_PAGINA}"
        datos = _get(cliente, "tareas-service", url, token)
        if datos is None:
            datos = {"total": 0, "tareas": []}
        if not isinstance(datos, dict) or not isinstance(datos.get("tareas"), list):
            raise DependenciaNoDisponible("tareas-service", "listado de tareas con forma inesperada")

        for item in datos["tareas"]:
            if not isinstance(item, dict):
                continue
            tarea_id = primer_id(item.get("tarea_id"), item.get("tareaId"), item.get("id"))
            if not tarea_id:
                continue
            vistas.add(tarea_id)
            # tareaListadoItemSchema no trae usuario_id: se lo ponemos (filtramos por él).
            payload = {**item, "usuario_id": usuario_id}
            # Tampoco trae grupo_id ni hora_entrega: para tareas nuevas en la caché se pide el detalle.
            if "grupo_id" not in item and not db.get(TareaProyeccion, tarea_id):
                detalle = _get(cliente, "tareas-service", f"{base}/api/v1/tareas/{tarea_id}", token)
                if isinstance(detalle, dict):
                    payload = {**detalle, "usuario_id": usuario_id}
            aplicar_proyeccion(db, "tarea.actualizada", payload, commit=False)

        recibidas = len(datos["tareas"])
        total = entero_id(datos.get("total")) or 0
        tamano = entero_id(datos.get("tamano")) or TAMANO_PAGINA
        if recibidas == 0 or pagina * tamano >= total:
            completo = True
            break

    db.flush()
    if not completo:
        log.warning("Listado de tareas truncado a %s páginas para usuario_id=%s", MAX_PAGINAS, usuario_id)
        return
    # Con el listado completo, lo que tareas-service ya no devuelve se quita de la caché.
    sobrantes = db.query(TareaProyeccion).filter(TareaProyeccion.usuario_id == usuario_id)
    if vistas:
        sobrantes = sobrantes.filter(TareaProyeccion.id.notin_(vistas))
    sobrantes.delete(synchronize_session=False)


def _sincronizar_materias(db: Session, cliente: httpx.Client, base: str, usuario_id: int, token: str | None) -> None:
    # Ver contrato, sección E: el filtro ?usuario_id= está en discusión; con el JWT del
    # usuario materias-service devuelve "mis materias" de todas formas.
    datos = _get(cliente, "materias-service", f"{base}/api/v1/materias?usuario_id={usuario_id}", token)
    for materia in datos if isinstance(datos, list) else []:
        if isinstance(materia, dict):
            aplicar_proyeccion(db, "materia.actualizada", materia, commit=False)

    # Materias usadas por las tareas del usuario que aún no tienen nombre en caché.
    ids = {
        fila.materia_id
        for fila in db.query(TareaProyeccion.materia_id).filter(TareaProyeccion.usuario_id == usuario_id)
        if fila.materia_id
    }
    for materia_id in ids:
        if db.get(MateriaProyeccion, materia_id):
            continue
        detalle = _get(cliente, "materias-service", f"{base}/api/v1/materias/{materia_id}", token)
        if isinstance(detalle, dict):
            aplicar_proyeccion(db, "materia.actualizada", {**detalle, "materia_id": materia_id}, commit=False)


def _es_integrante(integrante: Any, usuario_id: int) -> bool:
    if isinstance(integrante, dict):
        return primer_id(integrante.get("usuario_id"), integrante.get("usuarioId")) == usuario_id
    return entero_id(integrante) == usuario_id


def _sincronizar_grupos(db: Session, cliente: httpx.Client, base: str, usuario_id: int, token: str | None) -> None:
    datos = _get(cliente, "grupos-service", f"{base}/api/v1/grupos", token)
    if datos is None:
        datos = []
    if not isinstance(datos, list):
        raise DependenciaNoDisponible("grupos-service", "listado de grupos con forma inesperada")

    mios: set[int] = set()
    for grupo in datos:
        if not isinstance(grupo, dict):
            continue
        grupo_id = primer_id(grupo.get("grupo_id"), grupo.get("grupoId"), grupo.get("id"))
        if not grupo_id or not any(_es_integrante(i, usuario_id) for i in grupo.get("integrantes") or []):
            continue
        mios.add(grupo_id)
        aplicar_proyeccion(db, "grupo.actualizado", grupo, commit=False)

    db.flush()
    # Grupos de los que el usuario ya salió.
    salidas = db.query(MiembroGrupo).filter(MiembroGrupo.usuario_id == usuario_id)
    if mios:
        salidas = salidas.filter(MiembroGrupo.grupo_id.notin_(mios))
    salidas.delete(synchronize_session=False)


Paso = Callable[[Session, httpx.Client, str, int, str | None], None]


def refrescar_usuario(db: Session, usuario_id: int, autorizacion: str | None = None) -> ResultadoSincronizacion:
    """Actualiza la caché de un usuario. Si no hay URLs configuradas, no hace nada (modo demo/eventos)."""
    resultado = ResultadoSincronizacion()
    if not hay_servicios_configurados():
        return resultado

    registro = db.get(SincronizacionUsuario, usuario_id) or SincronizacionUsuario(usuario_id=usuario_id)
    momento = ahora()
    token = _autorizacion(autorizacion)
    # Tareas antes que materias: así se sabe qué materias faltan por nombre.
    pasos: list[tuple[str, str, Paso]] = [
        ("usuarios-service", settings.usuarios_service_url, _sincronizar_usuario),
        ("tareas-service", settings.tareas_service_url, _sincronizar_tareas),
        ("materias-service", settings.materias_service_url, _sincronizar_materias),
        ("grupos-service", settings.grupos_service_url, _sincronizar_grupos),
    ]

    with _crear_cliente() as cliente:
        for servicio, base, paso in pasos:
            if not base:
                continue
            campo = _CAMPO_POR_SERVICIO[servicio]
            ultima = getattr(registro, campo)
            if ultima and (momento - ultima).total_seconds() < settings.cache_ttl_seconds:
                continue
            try:
                paso(db, cliente, base.rstrip("/"), usuario_id, token)
            except DependenciaNoDisponible as exc:
                db.rollback()
                log.warning(
                    "Dependencia no disponible servicio=%s usuario_id=%s hora=%s detalle=%s",
                    servicio,
                    usuario_id,
                    momento.isoformat(timespec="seconds"),
                    exc.detalle,
                )
                resultado.fallidos.append(servicio)
                continue
            setattr(registro, campo, momento)
            registro = db.merge(registro)
            db.commit()

    resultado.registro = db.get(SincronizacionUsuario, usuario_id)
    return resultado
