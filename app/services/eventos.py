import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    EventoRecibido,
    GrupoProyeccion,
    MateriaProyeccion,
    MiembroGrupo,
    TareaProyeccion,
    UsuarioProyeccion,
)
from app.schemas import EventoEntrada, EventoRespuesta
from app.services.ids import entero_id, primer_id
from app.services.tiempo import ahora, normalizar_estado, parsear_fecha, parsear_fecha_entrega


def aplicar_proyeccion(db: Session, tipo: str, payload: dict, occurred_at: datetime | None = None) -> None:
    _aplicar(db, tipo, payload, occurred_at)
    db.commit()


def procesar_evento(db: Session, entrada: EventoEntrada) -> EventoRespuesta:
    evento_id = entrada.evento_id or str(uuid.uuid4())
    existente = db.query(EventoRecibido).filter_by(evento_id=evento_id).first()
    if existente:
        return EventoRespuesta(
            aceptado=True,
            duplicado=True,
            evento_id=evento_id,
            tipo=entrada.evento,
            mensaje="Evento ya procesado (idempotencia).",
        )

    _aplicar(db, entrada.evento, entrada.payload, entrada.occurred_at)
    db.add(
        EventoRecibido(
            evento_id=evento_id,
            tipo=entrada.evento,
            payload_json=json.dumps(entrada.payload, default=str, ensure_ascii=False),
            recibido_en=ahora(),
        )
    )
    db.commit()
    return EventoRespuesta(
        aceptado=True,
        duplicado=False,
        evento_id=evento_id,
        tipo=entrada.evento,
        mensaje="Evento aplicado a la caché local.",
    )


def _aplicar(db: Session, tipo: str, payload: dict, occurred_at: datetime | None) -> None:
    manejadores = {
        "usuario.registrado": _usuario,
        "usuario.actualizado": _usuario,
        "materia.creada": _materia,
        "materia.actualizada": _materia,
        "grupo.creado": _grupo,
        "grupo.actualizado": _grupo,
        "grupo.miembro_agregado": _miembro,
        "tarea.creada": _tarea,
        "tarea.actualizada": _tarea,
        "tarea.estado_cambiado": _tarea,
        "tarea.eliminada": _eliminar_tarea,
        "tarea_creada": _tarea,
    }
    manejador = manejadores.get(tipo)
    if manejador:
        manejador(db, payload, occurred_at)


def _usuario(db: Session, payload: dict, _: datetime | None) -> None:
    usuario_id = primer_id(payload.get("usuario_id"), payload.get("usuarioId"), payload.get("id"))
    if not usuario_id:
        return
    usuario = db.get(UsuarioProyeccion, usuario_id) or UsuarioProyeccion(id=usuario_id)
    usuario.nombre = payload.get("nombre", usuario.nombre or f"Usuario {usuario_id}")
    usuario.email = payload.get("email") or payload.get("correo") or usuario.email
    usuario.rol = payload.get("rol", usuario.rol or "estudiante")
    db.merge(usuario)


def _materia(db: Session, payload: dict, _: datetime | None) -> None:
    materia_id = primer_id(payload.get("materia_id"), payload.get("materiaId"), payload.get("id"))
    if not materia_id:
        return
    materia = db.get(MateriaProyeccion, materia_id) or MateriaProyeccion(id=materia_id)
    materia.nombre = payload.get("nombre", materia.nombre or f"Materia {materia_id}")
    materia.nrc = str(payload.get("nrc") or payload.get("codigo") or materia.nrc or "")
    db.merge(materia)


def _grupo(db: Session, payload: dict, _: datetime | None) -> None:
    grupo_id = primer_id(payload.get("grupo_id"), payload.get("grupoId"), payload.get("id"))
    if not grupo_id:
        return
    grupo = db.get(GrupoProyeccion, grupo_id) or GrupoProyeccion(id=grupo_id)
    grupo.nombre = payload.get("nombre", grupo.nombre or f"Grupo {grupo_id}")
    grupo.materia_id = primer_id(payload.get("materia_id"), payload.get("materiaId"), grupo.materia_id) or grupo.materia_id
    grupo.creado_por = primer_id(payload.get("creado_por"), payload.get("creadoPor"), grupo.creado_por) or grupo.creado_por
    db.merge(grupo)
    for integrante in payload.get("integrantes") or []:
        if isinstance(integrante, dict):
            _miembro(db, {"grupo_id": grupo_id, **integrante}, None)
        else:
            _miembro(db, {"grupo_id": grupo_id, "usuario_id": integrante}, None)


def _miembro(db: Session, payload: dict, _: datetime | None) -> None:
    grupo_id = primer_id(payload.get("grupo_id"), payload.get("grupoId"))
    usuario_id = primer_id(payload.get("usuario_id"), payload.get("usuarioId"), payload.get("id"))
    if not grupo_id or not usuario_id:
        return
    ya = db.query(MiembroGrupo).filter_by(grupo_id=grupo_id, usuario_id=usuario_id).first()
    if ya:
        if payload.get("rol"):
            ya.rol = payload["rol"]
        return
    db.add(MiembroGrupo(grupo_id=grupo_id, usuario_id=usuario_id, rol=payload.get("rol", "miembro")))


def _tarea(db: Session, payload: dict, occurred_at: datetime | None) -> None:
    tarea_id = primer_id(payload.get("tarea_id"), payload.get("tareaId"), payload.get("id"))
    if not tarea_id:
        return
    tarea = db.get(TareaProyeccion, tarea_id) or TareaProyeccion(id=tarea_id)
    if payload.get("titulo"):
        tarea.titulo = payload["titulo"]
    usuario_id = primer_id(payload.get("usuario_id"), payload.get("usuarioId"), payload.get("creadoPor"))
    if usuario_id:
        tarea.usuario_id = usuario_id
    materia_id = primer_id(payload.get("materia_id"), payload.get("materiaId"))
    if materia_id:
        tarea.materia_id = materia_id
    if "grupo_id" in payload or "grupoId" in payload:
        tarea.grupo_id = entero_id(payload.get("grupo_id", payload.get("grupoId")))
    if payload.get("prioridad"):
        tarea.prioridad = payload["prioridad"]
    if payload.get("estado"):
        tarea.estado = normalizar_estado(payload["estado"])
    if "fecha_entrega" in payload or "fechaEntrega" in payload:
        tarea.fecha_entrega = parsear_fecha_entrega(
            payload.get("fecha_entrega") or payload.get("fechaEntrega"),
            payload.get("hora_entrega") or payload.get("horaEntrega"),
        )
    if "fecha_completada" in payload or "fechaCompletada" in payload:
        tarea.fecha_completada = parsear_fecha(payload.get("fecha_completada") or payload.get("fechaCompletada"))
    elif tarea.estado == "completada" and not tarea.fecha_completada:
        tarea.fecha_completada = parsear_fecha(occurred_at) or ahora()
    if not tarea.creado_en:
        tarea.creado_en = parsear_fecha(payload.get("fecha_creacion") or payload.get("creadoEn")) or ahora()
    if not tarea.usuario_id:
        tarea.usuario_id = 0
    if not tarea.materia_id:
        tarea.materia_id = 0
    db.merge(tarea)


def _eliminar_tarea(db: Session, payload: dict, _: datetime | None) -> None:
    tarea_id = primer_id(payload.get("tarea_id"), payload.get("tareaId"), payload.get("id"))
    tarea = db.get(TareaProyeccion, tarea_id) if tarea_id else None
    if tarea:
        db.delete(tarea)
